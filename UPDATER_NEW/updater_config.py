# UPDATER_NEW/updater_config.py
"""
Configuration file for the RAG updater system.
Contains MongoDB and ChromaDB settings that match the existing scraper setup.
"""

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "rag_tracking_new"
MONGO_COLLECTION = "url_tracking_new"

# ChromaDB Configuration (matching settings.py)
CHROMA_DB_PATH = "./chroma_db_tech4"
CHROMA_COLLECTION_NAME = "scraped_content"
CHROMA_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
