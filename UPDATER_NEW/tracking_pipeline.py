# UPDATER_NEW/tracking_pipeline.py


import sys
import os
from pathlib import Path
import scrapy
from scrapy.exceptions import DropItem
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError
import chromadb

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Import configuration
from UPDATER_NEW.updater_config import (
    MONGO_URI, MONGO_DB, MONGO_COLLECTION,
    CHROMA_DB_PATH, CHROMA_COLLECTION_NAME
)

logger = logging.getLogger(__name__)


class MongoDBTrackingPipeline:
    """
    Pipeline that tracks content changes in MongoDB.
    
    Runs AFTER ChromaDBPipeline to ensure chunks are already stored.
    Manages change detection and ChromaDB cleanup for modified content.
    """
    
    @classmethod
    def from_crawler(cls, crawler):
        """
        Standard Scrapy method to instantiate pipeline from crawler.
        
        Args:
            crawler: Scrapy crawler instance
            
        Returns:
            Instance of MongoDBTrackingPipeline
        """
        return cls()
    
    def __init__(self):
        """
        Initialize MongoDB and ChromaDB connections.
        
        Sets up:
        - MongoDB connection and tracking collection
        - Unique index on URL field
        - ChromaDB client for chunk management
        - Statistics counters
        """
        logger.info("=" * 80)
        logger.info("Initializing MongoDBTrackingPipeline")
        logger.info("=" * 80)
        
        # MongoDB setup
        try:
            self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.mongo_client.server_info()
            logger.info("✓ Connected to MongoDB successfully")
            
            # Get database and collection
            self.db = self.mongo_client[MONGO_DB]
            self.url_tracking = self.db[MONGO_COLLECTION]
            
            # Create unique index on URL field
            self.url_tracking.create_index([("url", ASCENDING)], unique=True)
            logger.info(f"✓ MongoDB collection '{MONGO_DB}.{MONGO_COLLECTION}' ready with unique URL index")
            
        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {e}")
            logger.error("Make sure MongoDB is running on localhost:27017")
            raise
        
        # ChromaDB setup for managing deletions
        try:
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME
            )
            logger.info(f"✓ Connected to ChromaDB at '{CHROMA_DB_PATH}' (collection: '{CHROMA_COLLECTION_NAME}')")
        except Exception as e:
            logger.error(f"✗ Failed to connect to ChromaDB: {e}")
            raise
        
        # Statistics tracking
        self.urls_new = 0
        self.urls_modified = 0
        self.urls_unchanged = 0
        self.chunks_deleted = 0
        self.errors = 0
        
        logger.info("✓ MongoDBTrackingPipeline initialized successfully")
        logger.info("=" * 80)
    
    def _calculate_content_hash(self, text: str) -> str:
        """
        Calculate SHA256 hash of content for change detection.
        
        Args:
            text: The text content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _delete_old_chunks(self, url: str) -> int:
        """
        Delete old chunks from ChromaDB for a modified URL.
        
        Args:
            url: The URL whose chunks should be deleted
            
        Returns:
            Number of chunks deleted
        """
        try:
            # Query ChromaDB to get all chunks for this URL
            results = self.chroma_collection.get(
                where={"url": url},
                include=["metadatas"]
            )
            
            chunk_ids = results.get('ids', [])
            
            if chunk_ids:
                # Delete the chunks
                self.chroma_collection.delete(ids=chunk_ids)
                logger.debug(f"  ✓ Deleted {len(chunk_ids)} old chunks for URL: {url}")
                return len(chunk_ids)
            else:
                logger.debug(f"  No existing chunks found for URL: {url}")
                return 0
                
        except Exception as e:
            logger.error(f"  ✗ Error deleting chunks for {url}: {e}")
            return 0
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """
        Process item: detect changes and manage MongoDB BEFORE ChromaDB storage.
        
        This runs BEFORE ChromaDBPipeline, so we can prevent duplicate storage.
        
        Args:
            item: Scraped item with url, text, chunks, etc.
            spider: Spider instance
            
        Returns:
            Item (for new/modified content to proceed to ChromaDB)
            
        Raises:
            DropItem: For unchanged content (prevents ChromaDB duplicate storage)
        """
        url = item.get('url')
        text = item.get('text', '')
        # Normalize domain for storage
        domain = item.get('domain', '').lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        if not url or not text:
            logger.warning(f"  ⚠ Skipping item without URL or text")
            self.errors += 1
            return item
        
        try:
            # Calculate content hash
            content_hash = self._calculate_content_hash(text)
            
            # Get chunk count (chunks were created by ChunkingPipeline)
            chunk_count = len(item.get('chunks', []))
            
            # Check if URL exists in MongoDB
            existing_record = self.url_tracking.find_one({"url": url})
            
            if existing_record is None:
                # NEW URL - First time seeing this content
                logger.info(f"  ✓ NEW: {url} ({chunk_count} chunks) - will store in ChromaDB")
                
                # Prepare MongoDB document (will insert after ChromaDB storage succeeds)
                item['_tracking_action'] = 'insert'
                item['_tracking_document'] = {
                    'url': url,
                    'content_hash': content_hash,
                    'first_seen': datetime.utcnow(),
                    'last_checked': datetime.utcnow(),
                    'last_modified': datetime.utcnow(),
                    'chunk_count': chunk_count,
                    'status': 'active',
                    'domain': domain,
                    'title': item.get('title', ''),
                    'word_count': item.get('word_count', 0)
                }
                
                self.urls_new += 1
                
                # Return item - will proceed to ChromaDB
                return item
                
            else:
                # URL EXISTS - Check if content changed
                old_hash = existing_record.get('content_hash')
                
                if old_hash != content_hash:
                    # MODIFIED CONTENT - Delete old chunks BEFORE storing new ones
                    logger.info(f"  ⚠ MODIFIED: {url} - deleting old chunks, will store new ones")
                    
                    # Delete old chunks from ChromaDB NOW (before new storage)
                    deleted_count = self._delete_old_chunks(url)
                    self.chunks_deleted += deleted_count
                    
                    # Prepare MongoDB update (will execute after ChromaDB storage succeeds)
                    item['_tracking_action'] = 'update'
                    item['_tracking_update'] = {
                        'content_hash': content_hash,
                        'last_checked': datetime.utcnow(),
                        'last_modified': datetime.utcnow(),
                        'chunk_count': chunk_count,
                        'word_count': item.get('word_count', 0),
                        'title': item.get('title', '')
                    }
                    
                    self.urls_modified += 1
                    logger.info(f"  ✓ Deleted {deleted_count} old chunks - new chunks will be stored")
                    
                    # Return item - will proceed to ChromaDB
                    return item
                    
                else:
                    # UNCHANGED CONTENT - Do NOT store in ChromaDB
                    # Only update last_checked timestamp
                    self.url_tracking.update_one(
                        {"url": url},
                        {"$set": {'last_checked': datetime.utcnow()}}
                    )
                    
                    self.urls_unchanged += 1
                    logger.debug(f"  = UNCHANGED: {url} - skipping ChromaDB storage")
                    
                    # Drop the item - content hasn't changed, no need to store
                    # This prevents ChromaDB from receiving duplicate content
                    raise DropItem(f"Content unchanged - skipping ChromaDB storage: {url}")
                    
        except DropItem:
            # Re-raise DropItem to stop pipeline processing
            raise
            
        except DuplicateKeyError as e:
            logger.warning(f"  ⚠ Duplicate key error for {url}: {e}")
            self.urls_unchanged += 1
            # Drop to prevent duplicate ChromaDB storage
            raise DropItem(f"Duplicate URL detected: {url}")
            
        except PyMongoError as e:
            logger.error(f"  ✗ MongoDB error for {url}: {e}")
            self.errors += 1
            # Allow item to proceed - we'll try to store in ChromaDB anyway
            return item
            
        except Exception as e:
            logger.error(f"  ✗ Unexpected error tracking {url}: {e}", exc_info=True)
            self.errors += 1
            # Allow item to proceed - we'll try to store in ChromaDB anyway
            return item
    
    def close_spider(self, spider):
        """
        Called when spider closes. Log statistics and cleanup.
        
        Args:
            spider: Spider instance
        """
        total_processed = self.urls_new + self.urls_modified + self.urls_unchanged
        
        logger.info("=" * 80)
        logger.info("MONGODB TRACKING PIPELINE - FINAL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total URLs processed:  {total_processed}")
        logger.info(f"  New URLs added:      {self.urls_new}")
        logger.info(f"  Modified URLs:       {self.urls_modified}")
        logger.info(f"  Unchanged URLs:      {self.urls_unchanged}")
        logger.info(f"  Old chunks deleted:  {self.chunks_deleted}")
        logger.info(f"  Errors:              {self.errors}")
        logger.info("=" * 80)
        
        # Store statistics on spider for access in run_updater_simple.py
        spider.tracking_stats = {
            'urls_new': self.urls_new,
            'urls_modified': self.urls_modified,
            'urls_unchanged': self.urls_unchanged,
            'chunks_deleted': self.chunks_deleted,
            'errors': self.errors,
            'total': total_processed
        }
        
        # Close MongoDB connection
        try:
            self.mongo_client.close()
            logger.info("✓ MongoDB connection closed")
        except Exception as e:
            logger.error(f"✗ Error closing MongoDB connection: {e}")


class MongoDBFinalizerPipeline:
    """
    Pipeline that finalizes MongoDB records AFTER ChromaDB storage.
    
    Runs at priority 400 (after ChromaDBPipeline at 350) to complete
    the MongoDB tracking started by MongoDBTrackingPipeline.
    
    This ensures MongoDB is only updated if ChromaDB storage succeeds.
    """
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls()
    
    def __init__(self):
        """Initialize MongoDB connection."""
        logger.info("Initializing MongoDBFinalizerPipeline")
        
        try:
            self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.mongo_client.server_info()
            self.db = self.mongo_client[MONGO_DB]
            self.url_tracking = self.db[MONGO_COLLECTION]
            logger.info("✓ MongoDBFinalizerPipeline connected to MongoDB")
        except Exception as e:
            logger.error(f"✗ MongoDBFinalizerPipeline failed to connect: {e}")
            raise
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """
        Finalize MongoDB tracking after ChromaDB storage.
        
        Args:
            item: Item that was successfully stored in ChromaDB
            spider: Spider instance
            
        Returns:
            Item unchanged
        """
        tracking_action = item.get('_tracking_action')
        
        if not tracking_action:
            # No tracking action needed (error or unchanged item that somehow got through)
            return item
        
        url = item.get('url')
        
        try:
            if tracking_action == 'insert':
                # Insert new MongoDB record
                document = item.get('_tracking_document')
                if document:
                    try:
                        self.url_tracking.insert_one(document)
                        logger.debug(f"  ✓ MongoDB: Inserted new record for {url}")
                    except DuplicateKeyError:
                        logger.warning(f"  ⚠ MongoDB: URL already exists (concurrent insert): {url}")
                        
            elif tracking_action == 'update':
                # Update existing MongoDB record
                update_data = item.get('_tracking_update')
                if update_data:
                    self.url_tracking.update_one(
                        {"url": url},
                        {"$set": update_data}
                    )
                    logger.debug(f"  ✓ MongoDB: Updated record for {url}")
                    
        except Exception as e:
            logger.error(f"  ✗ MongoDB finalizer error for {url}: {e}")
        
        # Clean up tracking metadata from item
        item.pop('_tracking_action', None)
        item.pop('_tracking_document', None)
        item.pop('_tracking_update', None)
        
        return item
    
    def close_spider(self, spider):
        """Close MongoDB connection."""
        try:
            self.mongo_client.close()
            logger.info("✓ MongoDBFinalizerPipeline closed MongoDB connection")
        except Exception as e:
            logger.error(f"✗ Error closing MongoDB connection: {e}")
