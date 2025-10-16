# UPDATER_NEW/test_connection.py

import sys
import os
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
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


def test_mongodb():
    """Test MongoDB connection."""
    print("=" * 80)
    print("Testing MongoDB Connection")
    print("=" * 80)
    print(f"URI: {MONGO_URI}")
    print(f"Database: {MONGO_DB}")
    print(f"Collection: {MONGO_COLLECTION}")
    print()
    
    try:
        # Attempt connection
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.server_info()
        print("✅ MongoDB connection successful!")
        
        # Get database and collection
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        # Count documents
        count = collection.count_documents({})
        print(f"✅ Collection '{MONGO_COLLECTION}' accessible")
        print(f"   Total documents: {count}")
        
        if count > 0:
            # Get sample document
            sample = collection.find_one()
            if sample:
                print(f"   Sample URL: {sample.get('url', 'N/A')}")
                print(f"   Last checked: {sample.get('last_checked', 'N/A')}")
        
        # Get stats by domain
        pipeline = [
            {"$group": {
                "_id": "$domain",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        
        domains = list(collection.aggregate(pipeline))
        if domains:
            print(f"\n   Top domains:")
            for domain in domains:
                print(f"     - {domain['_id']}: {domain['count']} URLs")
        
        client.close()
        return True
        
    except ServerSelectionTimeoutError:
        print("❌ MongoDB connection timeout")
        print("   Is MongoDB running?")
        print("   Try: net start MongoDB")
        return False
        
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_chromadb():
    """Test ChromaDB connection."""
    print("\n" + "=" * 80)
    print("Testing ChromaDB Connection")
    print("=" * 80)
    print(f"Path: {CHROMA_DB_PATH}")
    print(f"Collection: {CHROMA_COLLECTION_NAME}")
    print()
    
    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        print("✅ ChromaDB client created successfully")
        
        # Try to get collection
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        print(f"✅ Collection '{CHROMA_COLLECTION_NAME}' accessible")
        
        # Count documents
        count = collection.count()
        print(f"   Total chunks: {count}")
        
        if count > 0:
            # Get sample
            sample = collection.get(limit=1, include=["metadatas"])
            if sample and sample.get('ids'):
                metadata = sample.get('metadatas', [{}])[0]
                print(f"   Sample chunk ID: {sample['ids'][0]}")
                print(f"   Sample URL: {metadata.get('url', 'N/A')}")
                print(f"   Sample domain: {metadata.get('domain', 'N/A')}")
        
        # Try a test query to verify embeddings work
        try:
            results = collection.query(
                query_texts=["test query"],
                n_results=1
            )
            print("✅ Query functionality working")
        except Exception as e:
            print(f"⚠️  Query test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")
        return False


def test_imports():
    """Test that all required imports work."""
    print("\n" + "=" * 80)
    print("Testing Python Imports")
    print("=" * 80)
    print()
    
    imports_ok = True
    
    # Test Scrapy
    try:
        import scrapy
        print(f"✅ scrapy {scrapy.__version__}")
    except ImportError as e:
        print(f"❌ scrapy import failed: {e}")
        imports_ok = False
    
    # Test Scrapy Playwright
    try:
        import scrapy_playwright
        print(f"✅ scrapy_playwright")
    except ImportError as e:
        print(f"❌ scrapy_playwright import failed: {e}")
        imports_ok = False
    
    # Test PyMongo
    try:
        import pymongo
        print(f"✅ pymongo {pymongo.__version__}")
    except ImportError as e:
        print(f"❌ pymongo import failed: {e}")
        imports_ok = False
    
    # Test ChromaDB
    try:
        import chromadb
        print(f"✅ chromadb {chromadb.__version__}")
    except ImportError as e:
        print(f"❌ chromadb import failed: {e}")
        imports_ok = False
    
    # Test existing spider
    try:
        from Scraping2.spiders.spider import FixedUniversalSpider
        print(f"✅ FixedUniversalSpider imported")
    except ImportError as e:
        print(f"❌ FixedUniversalSpider import failed: {e}")
        print(f"   Make sure you're running from the RAG directory root")
        imports_ok = False
    
    # Test updater spider
    try:
        from UPDATER_NEW.updater_wrapper import UpdaterSpider
        print(f"✅ UpdaterSpider imported")
    except ImportError as e:
        print(f"❌ UpdaterSpider import failed: {e}")
        imports_ok = False
    
    return imports_ok


def main():
    """Run all connection tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "RAG UPDATER - CONNECTION TEST" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    results = {
        'imports': test_imports(),
        'mongodb': test_mongodb(),
        'chromadb': test_chromadb()
    }
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name.upper()}")
    
    print("=" * 80)
    
    if all_passed:
        print("\n🎉 All tests passed! You're ready to run the updater.")
        print("\nNext step:")
        print("  python UPDATER_NEW\\run_updater_simple.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before running the updater.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
