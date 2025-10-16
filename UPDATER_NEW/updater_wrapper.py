# UPDATER_NEW/updater_wrapper.py
"""
UpdaterSpider: Extends FixedUniversalSpider for use with tracking pipeline.

This spider wraps the existing FixedUniversalSpider without modifying its code.
It inherits ALL scraping logic and works with MongoDBTrackingPipeline for change detection.

Key Features:
- Inherits ALL scraping logic from FixedUniversalSpider
- Works with MongoDBTrackingPipeline for change tracking (runs after ChromaDB storage)
- Logs statistics from pipeline after crawl completes
"""

import sys
import os
from pathlib import Path
import scrapy
import logging

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Import the existing spider
from Scraping2.spiders.spider import FixedUniversalSpider

logger = logging.getLogger(__name__)


class UpdaterSpider(FixedUniversalSpider):
    """
    Spider that extends FixedUniversalSpider for use with tracking pipeline.
    
    Uses parent's complete scraping logic without modification.
    MongoDBTrackingPipeline handles change detection and MongoDB tracking.
    """
    
    name = "updater_spider"
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the updater spider.
        
        Simply calls parent __init__ - no tracking setup needed here.
        MongoDBTrackingPipeline handles all tracking functionality.
        """
        # Initialize parent spider with all its functionality
        super().__init__(*args, **kwargs)
        
        # Initialize tracking stats (will be populated by pipeline)
        self.tracking_stats = {
            'urls_new': 0,
            'urls_modified': 0,
            'urls_unchanged': 0,
            'chunks_deleted': 0,
            'errors': 0,
            'total': 0
        }
        
        logger.info("=" * 80)
        logger.info("UpdaterSpider initialized - using FixedUniversalSpider parsing logic")
        logger.info("MongoDBTrackingPipeline will handle change detection")
        logger.info("=" * 80)
    
    def closed(self, reason):
        """
        Called when spider closes. Log statistics from tracking pipeline.
        
        Args:
            reason: Reason for spider closure
        """
        logger.info("=" * 80)
        logger.info("UPDATER SPIDER COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Reason: {reason}")
        logger.info("")
        
        # Log statistics from tracking pipeline
        if hasattr(self, 'tracking_stats') and self.tracking_stats['total'] > 0:
            logger.info("TRACKING STATISTICS (from MongoDBTrackingPipeline):")
            logger.info(f"  Total URLs processed:  {self.tracking_stats['total']}")
            logger.info(f"  New URLs added:        {self.tracking_stats['urls_new']}")
            logger.info(f"  Modified URLs:         {self.tracking_stats['urls_modified']}")
            logger.info(f"  Unchanged URLs:        {self.tracking_stats['urls_unchanged']}")
            logger.info(f"  Old chunks deleted:    {self.tracking_stats['chunks_deleted']}")
            logger.info(f"  Errors:                {self.tracking_stats['errors']}")
        else:
            logger.info("No tracking statistics available")
            logger.info("(MongoDBTrackingPipeline may not have been configured)")
        
        logger.info("=" * 80)
        
        # Call parent's closed method if it exists
        if hasattr(super(), 'closed'):
            super().closed(reason)
