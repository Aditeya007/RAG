# UPDATER_NEW/run_updater_simple.py
"""
Interactive CLI script to run the RAG updater system.

This script:
1. Gets URL input from user
2. Checks MongoDB for existing records
3. Runs UpdaterSpider (which uses FixedUniversalSpider logic + MongoDB tracking)
4. Reports statistics on new, modified, and unchanged content

Usage (from RAG root):
    python UPDATER_NEW\\run_updater_simple.py
"""

import sys
import os
from pathlib import Path
import logging
from urllib.parse import urlparse
from datetime import datetime
from pymongo import MongoClient
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Import configuration and spider
from UPDATER_NEW.updater_config import MONGO_URI, MONGO_DB, MONGO_COLLECTION
from UPDATER_NEW.updater_wrapper import UpdaterSpider


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('updater_run.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def get_user_input() -> tuple:
    """
    Get URL input from user with validation.
    
    Returns:
        Tuple of (start_url, domain, sitemap_url)
    """
    print("\n" + "=" * 80)
    print("RAG UPDATER SYSTEM - Interactive Mode")
    print("=" * 80)
    print()
    
    # Get start URL
    while True:
        start_url = input("Enter the starting URL to scrape: ").strip()
        
        if not start_url:
            print("❌ URL cannot be empty. Please try again.")
            continue
        
        if not start_url.startswith(('http://', 'https://')):
            print("❌ URL must start with http:// or https://")
            continue
        
        try:
            parsed = urlparse(start_url)
            if not parsed.netloc:
                print("❌ Invalid URL format. Please try again.")
                continue
            
            domain = parsed.netloc
            break
        except Exception as e:
            print(f"❌ Error parsing URL: {e}")
            continue
    
    # Normalize domain: lowercase, strip 'www.'
    norm_domain = domain.lower()
    if norm_domain.startswith('www.'):
        norm_domain = norm_domain[4:]
    print(f"✓ Domain extracted: {domain} (normalized: {norm_domain})")
    
    # Ask about sitemap
    sitemap_choice = input("\nDo you have a sitemap URL? (y/n, default: n): ").strip().lower()
    sitemap_url = None
    
    if sitemap_choice == 'y':
        sitemap_url = input("Enter sitemap URL: ").strip()
        if sitemap_url and not sitemap_url.startswith(('http://', 'https://')):
            print("⚠ Invalid sitemap URL format. Ignoring sitemap.")
            sitemap_url = None
        elif sitemap_url:
            print(f"✓ Will use sitemap: {sitemap_url}")
    
    return start_url, norm_domain, sitemap_url


def check_existing_records(domain: str) -> dict:
    """
    Check MongoDB for existing records for this domain.
    
    Args:
        domain: The domain to check
        
    Returns:
        Dict with statistics about existing records
    """
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Test connection
        
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        # Count records for this domain
        total_count = collection.count_documents({"domain": domain})
        active_count = collection.count_documents({"domain": domain, "status": "active"})
        
        stats = {
            'total': total_count,
            'active': active_count,
            'connection_success': True
        }
        
        # Get most recent update
        if total_count > 0:
            recent = collection.find_one(
                {"domain": domain},
                sort=[("last_checked", -1)]
            )
            if recent:
                stats['last_checked'] = recent.get('last_checked')
        
        client.close()
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        logger.error("Make sure MongoDB is running on localhost:27017")
        return {'connection_success': False, 'error': str(e)}


def print_existing_stats(stats: dict, domain: str):
    """
    Print statistics about existing records.
    
    Args:
        stats: Statistics dictionary from check_existing_records
        domain: The domain being checked
    """
    print("\n" + "-" * 80)
    print("EXISTING RECORDS CHECK")
    print("-" * 80)
    
    if not stats.get('connection_success'):
        print(f"❌ Could not connect to MongoDB: {stats.get('error', 'Unknown error')}")
        print("⚠  Will proceed with crawl, but tracking may fail.")
        return
    
    total = stats.get('total', 0)
    active = stats.get('active', 0)
    
    if total == 0:
        print(f"📊 No existing records found for domain: {domain}")
        print("🆕 This is a FIRST RUN - will scrape entire website")
        print("   All discovered URLs will be marked as NEW")
    else:
        print(f"📊 Found {total} existing records for domain: {domain}")
        print(f"   Active records: {active}")
        
        if 'last_checked' in stats:
            last_checked = stats['last_checked']
            print(f"   Last check: {last_checked.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        print("🔄 This is an UPDATE RUN - will detect changes")
        print("   - NEW: URLs not seen before")
        print("   - MODIFIED: URLs with changed content")
        print("   - UNCHANGED: URLs with same content")
    
    print("-" * 80)


def run_updater(start_url: str, domain: str, sitemap_url: str = None):
    """
    Run the updater spider with the given configuration.
    
    Args:
        start_url: Starting URL for the crawl
        domain: Domain to restrict crawling to
        sitemap_url: Optional sitemap URL
    """
    logger.info("=" * 80)
    logger.info("STARTING UPDATER SPIDER")
    logger.info("=" * 80)
    logger.info(f"Start URL: {start_url}")
    logger.info(f"Domain: {domain}")
    if sitemap_url:
        logger.info(f"Sitemap: {sitemap_url}")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        # Load existing Scrapy settings
        settings = get_project_settings()
        
        # Override spider module to include our updater spider
        settings.set('SPIDER_MODULES', ['Scraping2.spiders', 'UPDATER_NEW'])
        settings.set('NEWSPIDER_MODULE', 'UPDATER_NEW')
        
        # Configure pipeline order for intelligent update detection:
        # - ContentPipeline (300): Text cleaning, validation
        # - ChunkingPipeline (320): Creates chunks
        # - MongoDBTrackingPipeline (340): Detects NEW/MODIFIED/UNCHANGED, drops unchanged ⭐
        # - ChromaDBPipeline (350): Stores ONLY new/modified chunks (unchanged are dropped)
        # - MongoDBFinalizerPipeline (400): Finalizes MongoDB tracking after successful storage
        pipelines = settings.get('ITEM_PIPELINES', {})
        pipelines['UPDATER_NEW.tracking_pipeline.MongoDBTrackingPipeline'] = 340
        pipelines['UPDATER_NEW.tracking_pipeline.MongoDBFinalizerPipeline'] = 400
        settings.set('ITEM_PIPELINES', pipelines)
        
        logger.info("=" * 80)
        logger.info("INTELLIGENT UPDATE PIPELINE ORDER:")
        logger.info("=" * 80)
        logger.info("  300 - ContentPipeline (text cleaning & validation)")
        logger.info("  320 - ChunkingPipeline (create text chunks)")
        logger.info("  340 - MongoDBTrackingPipeline (detect changes, drop unchanged) ⭐")
        logger.info("  350 - ChromaDBPipeline (store ONLY new/modified content)")
        logger.info("  400 - MongoDBFinalizerPipeline (finalize tracking)")
        logger.info("=" * 80)
        logger.info("")
        logger.info("✓ Unchanged content will be detected and skipped BEFORE ChromaDB storage")
        logger.info("✓ Only NEW and MODIFIED content will be stored in ChromaDB")
        logger.info("✓ Output will match Scraping2 for new content, with smart updates")
        logger.info("")
        
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Configure spider arguments
        spider_kwargs = {
            'domain': domain,
            'start_url': start_url,
            'max_depth': 999,  # Deep crawl
            'max_links_per_page': 1000,
            'respect_robots': False,
            'aggressive_discovery': True
        }
        
        if sitemap_url:
            spider_kwargs['sitemap_url'] = sitemap_url
        
        # Start the crawl
        process.crawl(UpdaterSpider, **spider_kwargs)
        process.start()  # Blocking call
        
        logger.info("=" * 80)
        logger.info("CRAWL COMPLETED SUCCESSFULLY")
        logger.info(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠ Crawl interrupted by user (Ctrl+C)")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Error running crawler: {e}", exc_info=True)
        sys.exit(1)


def main():
    """
    Main entry point for the updater script.
    """
    try:
        # Get user input
        start_url, domain, sitemap_url = get_user_input()
        
        # Check for existing records
        stats = check_existing_records(domain)
        print_existing_stats(stats, domain)
        
        # Confirm before starting
        print("\n" + "=" * 80)
        confirm = input("Start crawling? (y/n, default: y): ").strip().lower()
        if confirm == 'n':
            print("❌ Crawl cancelled by user")
            sys.exit(0)
        
        # Run the updater
        run_updater(start_url, domain, sitemap_url)
        
        # Final message
        print("\n" + "=" * 80)
        print("✅ UPDATER RUN COMPLETED")
        print("=" * 80)
        print("Check the logs above for detailed statistics.")
        print("Log file: updater_run.log")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
