# UPDATER_NEW/__init__.py
"""
RAG Updater System

This package provides intelligent change detection and incremental updates
for the RAG web scraper system.

Components:
- updater_config: Configuration settings
- updater_wrapper: UpdaterSpider class
- run_updater_simple: Interactive CLI script
"""

__version__ = "1.0.0"
__author__ = "RAG Team"

from .updater_config import (
    MONGO_URI,
    MONGO_DB,
    MONGO_COLLECTION,
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME
)

from .updater_wrapper import UpdaterSpider

__all__ = [
    'UpdaterSpider',
    'MONGO_URI',
    'MONGO_DB',
    'MONGO_COLLECTION',
    'CHROMA_DB_PATH',
    'CHROMA_COLLECTION_NAME'
]
