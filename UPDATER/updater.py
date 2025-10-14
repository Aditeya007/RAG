# updater.py - RAG Database Updater (FIXED)
# Scans website for changes and uses the same spider to scrape and store updates

import sys
import os

# Add the parent directory to Python path to find Scraping2 module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scrapy
import hashlib
import logging
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import urlparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.linkextractors import LinkExtractor

# Import configuration
try:
    from config import (
        MONGO_URI, MONGO_DATABASE, MONGO_COLLECTION_URL_TRACKING,
        CHROMA_DB_PATH, CHROMA_COLLECTION_NAME, CHROMA_EMBEDDING_MODEL,
        MINIMUM_CONTENT_LENGTH, METADATA_FIELDS, CHUNK_BATCH_SIZE,
        MAX_RETRIES, RETRY_DELAY
    )
except ImportError:
    # Fallback defaults if config.py doesn't exist
    MONGO_URI = "mongodb://localhost:27017/"
    MONGO_DATABASE = "rag_updater"
    MONGO_COLLECTION_URL_TRACKING = "url_tracking"
    CHROMA_DB_PATH = "./chroma_db_tech2"
    CHROMA_COLLECTION_NAME = "scraped_content"
    CHROMA_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    MINIMUM_CONTENT_LENGTH = 100
    CHUNK_BATCH_SIZE = 50
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    METADATA_FIELDS = [
        'url', 'title', 'content_type', 'extraction_method',
        'page_depth', 'response_status', 'content_length',
        'page_title', 'meta_description', 'extracted_at',
        'scraped_at', 'word_count', 'domain', 'text_length'
    ]

logger = logging.getLogger(__name__)

# Import the exact spider and items you're already using
try:
    from Scraping2.spiders.spider import FixedUniversalSpider
    from Scraping2.items import ScrapedContentItem
except ImportError:
    logger.error("Could not import Scraping2 modules")
    raise


class ContentChangeDetectorSpider(FixedUniversalSpider):
    """
    Extends your existing FixedUniversalSpider to detect content changes.
    """

    name = "content_change_detector"

    def __init__(self, domain: str, start_url: str, mongo_uri=None, *args, **kwargs):
        # Extract domain from URL if full URL provided and remove port
        if domain.startswith('http://') or domain.startswith('https://'):
            parsed = urlparse(domain)
            domain = parsed.netloc.split(':')[0]  # Remove port if exists
        else:
            # Handle domain with port (e.g., localhost:8000)
            domain = domain.split(':')[0] # Remove port if exists
        if 'localhost' in start_url.lower():
            start_url = start_url.replace('localhost', '127.0.0.1')
            start_url = start_url.replace('LOCALHOST', '127.0.0.1')

        # Set max_depth to 1 by default
        max_depth = kwargs.get('max_depth', 1)

        # Initialize parent spider
        super().__init__(
            domain=domain,
            start_url=start_url,
            max_depth=max_depth,
            sitemap_url=kwargs.get('sitemap_url'),
            max_links_per_page=kwargs.get('max_links_per_page', 1000),
            respect_robots=kwargs.get('respect_robots', True),
            aggressive_discovery=kwargs.get('aggressive_discovery', True)
        )

        # MongoDB connection
        self.mongo_uri = mongo_uri or MONGO_URI
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client[MONGO_DATABASE]
        self.url_tracking = self.db[MONGO_COLLECTION_URL_TRACKING]
        self.url_tracking.create_index("url", unique=True)

        # Store URL status for pipeline access
        self.url_status = {}  # url -> update_status

        # Statistics
        self.urls_checked = 0
        self.urls_new = 0
        self.urls_modified = 0
        self.urls_unchanged = 0
        self.urls_sent_to_pipeline = 0

        logger.info(f"🔄 ContentChangeDetectorSpider initialized")
        logger.info(f"📊 MongoDB: {self.mongo_uri}")
        logger.info(f"📂 Database: {MONGO_DATABASE}")
        logger.info(f"📋 Collection: {MONGO_COLLECTION_URL_TRACKING}")
        logger.info(f"🎯 Target: {start_url}")
        logger.info(f"🌐 Allowed domains: {self.allowed_domains}")

    def _should_process_url(self, url: str) -> bool:
        """Override parent method with better binary file detection for HTML pages"""
        if not url:
            return False
        
        # First check if already fully processed
        if self._is_url_already_processed(url):
            logger.debug(f"🔄 Skipping already processed URL: {url}")
            return False
            
        try:
            parsed = urlparse(url)
            # Domain checking
            if not any(d in parsed.netloc for d in self.allowed_domains):
                return False
            
            # Only skip URLs with clearly binary extensions
            binary_extensions = [
                # Documents
                ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".rtf", ".odt", ".ods", ".odp",
                # Archives  
                ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
                # Executables
                ".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm",
                # Media files
                ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
                ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm",
                ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma",
                # Fonts
                ".ttf", ".otf", ".woff", ".woff2", ".eot"
            ]
            
            # Check against binary extensions only
            if any(parsed.path.lower().endswith(ext) for ext in binary_extensions):
                logger.debug(f"Skipping binary file URL: {url}")
                return False
                
            # Allow URLs without extensions (like http://127.0.0.1:8001/)
            # Allow .html, .htm, .php, .asp, .txt, .css, .js, .xml, .json
                
            if len(url) > 2000:
                return False
            return True
        except Exception:
            return True  # Default to True on error

    def _is_binary_content(self, response):
        """Check if response contains binary content based on headers"""
        content_type = (response.headers.get("Content-Type") or b"").decode("latin1").lower()
        
        # Skip binary content types
        binary_content_types = [
            "image/", "video/", "audio/", "application/pdf", "application/zip", 
            "application/octet-stream", "application/x-executable", "application/x-msdownload"
        ]
        
        if any(binary_type in content_type for binary_type in binary_content_types):
            return True
            
        # Allow text and HTML content
        allowed_content_types = [
            "text/html", "text/plain", "text/css", "text/javascript",
            "application/json", "application/xml", "application/xhtml+xml"
        ]
        
        if any(allowed_type in content_type for allowed_type in allowed_content_types):
            return False
            
        # Default to allowing if content type is unclear
        return False

    def start_requests(self):
        """Override start_requests to use our parse method"""
        headers = self._get_default_headers()

        # Process start URLs with our custom parse method
        for url in self.start_urls:
            logger.info(f"🎯 Yielding start URL: {url}")
            yield scrapy.Request(
                url,
                callback=self.parse,  # Use our custom parse method
                errback=self.handle_error,
                headers=headers,
                meta={
                    "depth": 0,
                    "playwright": False,
                    "dont_cache": True,
                    "from_sitemap": False,
                    "url_source": "start_url",
                },
                priority=1000,
                dont_filter=True,
            )

        # Phase 2: sitemap discovery (lower priority) - route to parse as well
        if self.sitemap_url:
            yield scrapy.Request(
                self.sitemap_url,
                callback=self.parse_sitemap,  # Keep sitemap parsing separate
                headers=headers,
                meta={"dont_cache": True, "sitemap_attempt": True, "depth": 0},
                priority=900,
                errback=self.handle_sitemap_error,
            )

    def parse(self, response):
        """Override parse to add change detection"""
        try:
            # Skip already processed URLs
            if self._is_url_already_processed(response.url):
                logger.info(f"⏭️ Skipping already processed page: {response.url}")
                return
            
            self._mark_url_as_processing(response.url)
            self.urls_checked += 1
            
            url = response.url
            logger.info(f"🔍 Processing: {url}")
            logger.debug(f"✅ Processing URL: {response.url}")
            
            # === CONTENT EXTRACTION (matching spider.py) ===
            full_text = response.css("body").xpath("normalize-space(string(.))").get()
            title = response.css("title::text").get()
            meta_description = response.css(
                'meta[name="description"]::attr(content), '
                'meta[property="og:description"]::attr(content)'
            ).get()
            alt_text_list = response.css('img::attr(alt), figure figcaption::text').getall()
            alt_text = " ".join(alt for alt in alt_text_list if alt and alt.strip()) if alt_text_list else ""
            
            # Combine all text
            combined_text_parts = []
            if full_text and len(full_text.strip()) >= 50:
                combined_text_parts.append(full_text.strip())
            if title and title.strip():
                combined_text_parts.append(title.strip())
            if meta_description and len(meta_description.strip()) >= 15:
                combined_text_parts.append(meta_description.strip())
            if alt_text and len(alt_text.strip()) >= 10:
                combined_text_parts.append(alt_text.strip())
            
            raw_combined_text = " ".join(combined_text_parts)
            
            logger.info(f"🔍 Raw combined text length: {len(raw_combined_text)}")
            logger.info(f"🔍 First 500 chars: {raw_combined_text[:500] if raw_combined_text else 'EMPTY'}")
            
            # Clean the text
            cleaned_text = self._clean_webpage_text(raw_combined_text) if raw_combined_text else ""
            
            # === VALIDATION ===
            if not cleaned_text or len(cleaned_text.strip()) < 50:
                logger.info(f"⏭️ Insufficient content ({len(cleaned_text) if cleaned_text else 0} chars): {url}")
                yield from self._extract_links(response)
                return  # <-- CRITICAL: Must return here
            
            # === HASH CALCULATION ===
            content_hash = hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()
            
            logger.info(f"✅ Extracted {len(cleaned_text)} chars, hash: {content_hash[:8]}...")
            
            # === CHANGE DETECTION ===
            existing_record = self.url_tracking.find_one({"url": url})
            
            should_yield = False
            update_status = "unknown"
            
            if not existing_record:
                # New URL
                should_yield = True
                update_status = "new"
                self.urls_new += 1
                logger.info(f"✨ NEW: {url}")
            elif existing_record.get("content_hash") != content_hash:
                # Modified URL
                should_yield = True
                update_status = "modified"
                self.urls_modified += 1
                logger.info(f"🔄 MODIFIED: {url}")
            else:
                # Unchanged
                should_yield = False
                update_status = "unchanged"
                self.urls_unchanged += 1
                logger.info(f"⏭️ UNCHANGED: {url}")
                # Still update last_checked timestamp
                self.url_tracking.update_one(
                    {"url": url},
                    {"$set": {"last_checked": datetime.utcnow()}}
                )
            
            # === YIELD ITEM TO PIPELINE ===
            if should_yield:
                self.urls_sent_to_pipeline += 1
                
                item = ScrapedContentItem()
                item['url'] = url
                item['text'] = cleaned_text
                item['title'] = title or ""
                item['content_type'] = "webpage"
                item['scraped_with_playwright'] = False
                item['timestamp'] = datetime.utcnow().isoformat()
                item['domain'] = urlparse(url).netloc
                item['scraped_at'] = datetime.utcnow().isoformat()
                item['text_length'] = len(cleaned_text)
                item['word_count'] = len(cleaned_text.split())
                
                logger.info(f"📦 Yielding item for pipeline: {url}")
                yield item
                
                # Store status for pipeline
                self.url_status[url] = update_status
            
            # === EXTRACT LINKS ===
            yield from self._extract_links(response)
            
            # Mark as fully processed
            self._mark_url_as_fully_processed(response.url)
            
        except Exception as e:
            logger.error(f"Error in parse method for {response.url}: {e}")
            try:
                yield from self._extract_links(response)
            except Exception:
                pass


    def _extract_links(self, response):
        """Extract and follow links using parent spider's logic"""
        try:
            current_depth = response.meta.get("depth", 0)
            if self.max_depth and current_depth >= self.max_depth:
                return

            # Use improved binary detection for link extraction
            binary_extensions = [
                # Documents
                "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "rtf", "odt", "ods", "odp",
                # Archives  
                "zip", "rar", "7z", "tar", "gz", "bz2",
                # Executables
                "exe", "msi", "dmg", "pkg", "deb", "rpm",
                # Media files
                "jpg", "jpeg", "png", "gif", "svg", "ico", "webp",
                "mp4", "avi", "mov", "wmv", "flv", "mkv", "webm",
                "mp3", "wav", "flac", "aac", "ogg", "wma",
                # Fonts
                "ttf", "otf", "woff", "woff2", "eot"
            ]
            
            link_extractor = LinkExtractor(
                allow_domains=self.allowed_domains,
                unique=True,
                deny_extensions=binary_extensions,  # Only deny truly binary files
                canonicalize=True
            )

            links = [l.url for l in link_extractor.extract_links(response)]
            logger.info(f"🔗 Found {len(links)} links on {response.url}")

            # Additional aggressive discovery if enabled
            if self.aggressive_discovery:
                extra_selectors = [
                    'a::attr(href)',
                    'nav a::attr(href)',
                    'header a::attr(href)',
                    'footer a::attr(href)',
                    '.menu a::attr(href)',
                    '.navigation a::attr(href)',
                ]
                for sel in extra_selectors:
                    try:
                        extra_links = response.css(sel).getall()
                        links.extend(extra_links)
                    except Exception:
                        pass

            followed = 0
            seen = set()
            for href in links:
                if not href or href in seen:
                    continue
                seen.add(href)
                if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                    continue
                
                absolute_url = self._canonicalize_url(response.urljoin(href))
                
                # Double-check URL filtering before yielding request
                if not self._should_process_url(absolute_url):
                    logger.debug(f"Filtering out binary file URL: {absolute_url}")
                    continue
                    
                if not self._should_follow_link(absolute_url):
                    continue
                
                # Skip if already processed
                if self._is_url_already_processed(absolute_url):
                    logger.debug(f"🔄 Skipping already processed URL: {absolute_url}")
                    continue

                if followed >= self.max_links_per_page:
                    break

                followed += 1
                logger.debug(f"  Following: {absolute_url}")
                yield scrapy.Request(
                    absolute_url,
                    callback=self.parse,
                    errback=self.handle_error,
                    meta={
                        "depth": current_depth + 1,
                        "from_sitemap": response.meta.get("from_sitemap", False),
                    },
                    dont_filter=False
                )

        except Exception as e:
            logger.error(f"❌ Error extracting links from {response.url}: {e}")

    def closed(self, reason):
        """Spider closed callback"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🛑 UPDATER SPIDER CLOSED - Reason: {reason}")
        logger.info(f"{'='*80}")
        logger.info(f"📊 URLs Checked: {self.urls_checked}")
        logger.info(f"✅ New URLs: {self.urls_new}")
        logger.info(f"🔄 Modified URLs: {self.urls_modified}")
        logger.info(f"⏭️ Unchanged URLs: {self.urls_unchanged}")
        logger.info(f"📦 Items Sent to Pipeline: {self.urls_sent_to_pipeline}")
        logger.info(f"{'='*80}\n")

        self.mongo_client.close()


class UpdaterChromaDBPipeline:
    """Enhanced ChromaDB pipeline that handles content updates"""

    def __init__(self):
        self.client = None
        self.collection = None
        self.mongo_client = None
        self.url_tracking = None
        self.batch_size = CHUNK_BATCH_SIZE
        self.batch_items = []
        self.items_stored = 0
        self.stored_ids = set()
        self.max_retries = MAX_RETRIES
        self.retry_delay = RETRY_DELAY
        self.metadata_fields = METADATA_FIELDS
        self.db_path = CHROMA_DB_PATH
        self.collection_name = CHROMA_COLLECTION_NAME
        self.embedding_model_name = CHROMA_EMBEDDING_MODEL

    def open_spider(self, spider):
        """Initialize ChromaDB and MongoDB connections"""
        import chromadb
        try:
            import chromadb.utils.embedding_functions as embedding_functions
        except ImportError:
            try:
                from chromadb.utils import embedding_functions
            except ImportError:
                from chromadb import embedding_functions

        self.client = chromadb.PersistentClient(path=self.db_path)
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model_name
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_function
        )

        mongo_uri = getattr(spider, 'mongo_uri', MONGO_URI)
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client[MONGO_DATABASE]
        self.url_tracking = self.db[MONGO_COLLECTION_URL_TRACKING]

        logger.info(f"✅ UpdaterChromaDBPipeline initialized")
        logger.info(f"   ChromaDB: {self.db_path}")
        logger.info(f"   Collection: {self.collection_name}")
        logger.info(f"   MongoDB: {MONGO_DATABASE}.{MONGO_COLLECTION_URL_TRACKING}")

    def close_spider(self, spider):
        """Process remaining batch and close connections"""
        if self.batch_items:
            self._process_batch()

        logger.info(f"✅ UpdaterChromaDBPipeline finished. Total chunks stored: {self.items_stored}")
        if self.mongo_client:
            self.mongo_client.close()

    def process_item(self, item, spider):
        """Process item and handle chunk deletion for updates"""
        import time

        url = item.get("url", "unknown")
        # Recalculate content hash from item text
        item_text = item.get("text", "")
        content_hash = hashlib.sha256(item_text.encode('utf-8')).hexdigest() if item_text else None
        # Get status from spider attribute
        update_status = getattr(spider, 'url_status', {}).get(url, "unknown")

        # Delete old chunks if modified
        if update_status == "modified":
            tracking_record = self.url_tracking.find_one({"url": url})
            if tracking_record and tracking_record.get("deletion_pending"):
                old_chunk_ids = tracking_record.get("old_chunk_ids_to_delete", [])
                if old_chunk_ids:
                    try:
                        self.collection.delete(ids=old_chunk_ids)
                        logger.info(f"🗑️ Deleted {len(old_chunk_ids)} old chunks for {url}")
                    except Exception as e:
                        logger.error(f"⚠️ Error deleting old chunks: {e}")

                    self.url_tracking.update_one(
                        {"url": url},
                        {"$unset": {"old_chunk_ids_to_delete": "", "deletion_pending": ""}}
                    )

        # Process chunks
        texts = item.get("chunks", [item.get("text", "")])
        chunk_ids = []

        for i, text in enumerate(texts):
            if not text.strip():
                continue

            chunk_hash = hashlib.md5(text.encode()).hexdigest()
            ts = str(int(time.time() * 1000000))
            chunk_index = str(i)
            doc_id = hashlib.md5(f"{url}_{chunk_hash}_{ts}_{chunk_index}".encode()).hexdigest()

            if doc_id in self.stored_ids:
                continue

            self.stored_ids.add(doc_id)
            chunk_ids.append(doc_id)

            metadata = {}
            for field in self.metadata_fields:
                if field in item:
                    value = item[field]
                    metadata[field] = value if isinstance(value, (str, int, float, bool)) else str(value)

            metadata.update({
                'unique_id': doc_id,
                'extraction_timestamp': ts,
                'chunk_length': len(text),
                'chunk_word_count': len(text.split()),
                'content_type': item.get('content_type', '')
            })

            self.batch_items.append({
                'id': doc_id,
                'document': text,
                'metadata': metadata
            })

            if len(self.batch_items) >= self.batch_size:
                self._process_batch()

        # Update MongoDB tracking
        self.url_tracking.update_one(
            {"url": url},
            {
                "$set": {
                    "content_hash": content_hash,
                    "chunk_ids": chunk_ids,
                    "last_modified": datetime.utcnow(),
                    "last_checked": datetime.utcnow(),
                    "status": "active",
                    "update_status": update_status,      # ALWAYS update status
                    "last_run_status": update_status     # Track most recent run
                },
                "$setOnInsert": {
                    "first_scraped": datetime.utcnow()
                }
            },
            upsert=True
        )

        return item

    def _process_batch(self):
        """Process batch with retry logic"""
        import time

        if not self.batch_items:
            return

        batch = self.batch_items
        self.batch_items = []

        for attempt in range(self.max_retries + 1):
            try:
                ids = [b['id'] for b in batch]
                documents = [b['document'] for b in batch]
                metadatas = [b['metadata'] for b in batch]

                # Remove duplicates within batch
                unique_ids = []
                unique_docs = []
                unique_metas = []
                seen_in_batch = set()

                for id_, doc, meta in zip(ids, documents, metadatas):
                    if id_ not in seen_in_batch:
                        unique_ids.append(id_)
                        unique_docs.append(doc)
                        unique_metas.append(meta)
                        seen_in_batch.add(id_)

                if unique_ids:
                    self.collection.add(
                        documents=unique_docs,
                        ids=unique_ids,
                        metadatas=unique_metas
                    )
                    self.items_stored += len(unique_ids)
                    logger.info(f"📦 ChromaDB stored {self.items_stored} total chunks (batch: {len(unique_ids)})")

                break

            except Exception as e:
                if "Expected IDs to be unique" in str(e):
                    logger.error(f"⚠️ Duplicate IDs in batch: {e}")
                    break
                elif attempt < self.max_retries:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning(f"⚠️ ChromaDB batch failed, retry in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    logger.error(f"❌ ChromaDB batch failed after retries: {e}")
                    break


def run_updater(domain, start_url, mongo_uri=None, max_depth=999, sitemap_url=None):
    """Run the updater"""
    settings = get_project_settings()

    settings['ITEM_PIPELINES'] = {
        'Scraping2.pipelines.ContentPipeline': 100,
        'Scraping2.pipelines.ChunkingPipeline': 200,
        'updater.UpdaterChromaDBPipeline': 300,
    }

    process = CrawlerProcess(settings)

    process.crawl(
        ContentChangeDetectorSpider,
        domain=domain,
        start_url=start_url,
        mongo_uri=mongo_uri,
        max_depth=1,  # Always set depth to 1
        sitemap_url=sitemap_url
    )

    process.start()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python updater.py <domain> <start_url> [mongo_uri]")
        print("Example: python updater.py localhost:8000 http://localhost:8000")
        sys.exit(1)

    domain = sys.argv[1]
    start_url = sys.argv[2]
    mongo_uri = sys.argv[3] if len(sys.argv) > 3 else None

    run_updater(domain, start_url, mongo_uri)
