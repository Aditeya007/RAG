# UPDATER_NEW/tracking_pipeline.py
"""
MongoDBTrackingPipeline: Tracks content changes AFTER ChromaDB storage.

This pipeline runs LAST in the pipeline chain (priority 400), ensuring:
1. Items have been validated (ContentPipeline)
2. Chunks have been created (ChunkingPipeline)
3. Chunks have been stored in ChromaDB (ChromaDBPipeline)

Only then does it track changes and manage MongoDB records.

Key Features:
- Detects NEW/MODIFIED/UNCHANGED content via SHA256 hashing
- Deletes old ChromaDB chunks for modified content
- Drops unchanged items to prevent duplicate processing
- Maintains statistics for reporting
"""

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
        Process item: track changes, manage MongoDB and ChromaDB.
        
        This runs AFTER ChromaDBPipeline, so chunks are already stored.
        
        Args:
            item: Scraped item with url, text, chunks, etc.
            spider: Spider instance
            
        Returns:
            Item (for new/modified content)
            
        Raises:
            DropItem: For unchanged content (prevents duplicate processing)
        """
        url = item.get('url')
        text = item.get('text', '')
        
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
                logger.info(f"  ✓ NEW: {url} ({chunk_count} chunks)")
                
                document = {
                    'url': url,
                    'content_hash': content_hash,
                    'first_seen': datetime.utcnow(),
                    'last_checked': datetime.utcnow(),
                    'last_modified': datetime.utcnow(),
                    'chunk_count': chunk_count,
                    'status': 'active',
                    'domain': item.get('domain', ''),
                    'title': item.get('title', ''),
                    'word_count': item.get('word_count', 0)
                }
                
                try:
                    self.url_tracking.insert_one(document)
                    self.urls_new += 1
                except DuplicateKeyError:
                    # Another thread inserted this URL
                    logger.warning(f"  ⚠ Duplicate key for URL (concurrent insert): {url}")
                    self.urls_unchanged += 1
                
                # Return item - chunks already stored by ChromaDBPipeline
                return item
                
            else:
                # URL EXISTS - Check if content changed
                old_hash = existing_record.get('content_hash')
                
                if old_hash != content_hash:
                    # MODIFIED CONTENT - Delete old chunks, update record
                    logger.info(f"  ⚠ MODIFIED: {url}")
                    
                    # Delete old chunks from ChromaDB
                    deleted_count = self._delete_old_chunks(url)
                    self.chunks_deleted += deleted_count
                    
                    # Update MongoDB record
                    self.url_tracking.update_one(
                        {"url": url},
                        {
                            "$set": {
                                'content_hash': content_hash,
                                'last_checked': datetime.utcnow(),
                                'last_modified': datetime.utcnow(),
                                'chunk_count': chunk_count,
                                'word_count': item.get('word_count', 0),
                                'title': item.get('title', '')
                            }
                        }
                    )
                    
                    self.urls_modified += 1
                    logger.info(f"  ✓ Updated: Deleted {deleted_count} old chunks, {chunk_count} new chunks already stored")
                    
                    # Return item - new chunks already stored by ChromaDBPipeline
                    return item
                    
                else:
                    # UNCHANGED CONTENT - Only update last_checked timestamp
                    self.url_tracking.update_one(
                        {"url": url},
                        {"$set": {'last_checked': datetime.utcnow()}}
                    )
                    
                    self.urls_unchanged += 1
                    logger.debug(f"  = UNCHANGED: {url}")
                    
                    # Drop the item - content hasn't changed
                    # ChromaDBPipeline already stored chunks, but since content
                    # is unchanged, we should have prevented duplicate storage
                    # NOTE: This happens AFTER ChromaDB storage, so we log it
                    # but the duplicate has already been added. This is a known
                    # limitation - unchanged detection happens post-storage.
                    raise DropItem(f"Content unchanged - skipping further processing: {url}")
                    
        except DropItem:
            # Re-raise DropItem to stop pipeline processing
            raise
            
        except DuplicateKeyError as e:
            logger.warning(f"  ⚠ Duplicate key error for {url}: {e}")
            self.urls_unchanged += 1
            return item
            
        except PyMongoError as e:
            logger.error(f"  ✗ MongoDB error for {url}: {e}")
            self.errors += 1
            return item
            
        except Exception as e:
            logger.error(f"  ✗ Unexpected error tracking {url}: {e}", exc_info=True)
            self.errors += 1
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
