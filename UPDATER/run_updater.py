# run_updater.py - Interactive RAG Updater
# Just run: python run_updater.py

import sys
import os
import logging
from datetime import datetime
from urllib.parse import urlparse

# Add the parent directory to Python path to find Scraping2 module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('rag_update_manual.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def print_banner():
    """Print startup banner"""
    print("\n" + "="*80)
    print("🤖 RAG DATABASE UPDATER")
    print("="*80)
    print("Detects and updates only changed content in your RAG database")
    print("="*80 + "\n")


def get_user_input():
    """Get URL from user interactively"""
    print("📝 Enter the website URL to update:")
    print("   (Example: https://example.com)")
    print()

    while True:
        start_url = input("🔗 URL: ").strip()

        if not start_url:
            print("❌ URL cannot be empty. Please try again.\n")
            continue

        # Add https:// if missing
        if not start_url.startswith(('http://', 'https://')):
            start_url = 'https://' + start_url
            print(f"   Added https:// → {start_url}")

        # Validate URL format
        try:
            parsed = urlparse(start_url)
            if not parsed.netloc:
                print("❌ Invalid URL format. Please try again.\n")
                continue

            domain = parsed.netloc

            # Confirm with user
            print(f"\n✓ Domain: {domain}")
            print(f"✓ Start URL: {start_url}")
            confirm = input("\nProceed with this URL? (y/n): ").strip().lower()

            if confirm in ['y', 'yes']:
                return domain, start_url
            else:
                print("\nLet's try again...\n")
                continue

        except Exception as e:
            print(f"❌ Error parsing URL: {e}")
            print("Please enter a valid URL.\n")
            continue


def ask_options():
    """Ask for optional settings"""
    print("\n" + "-"*80)
    print("⚙️  OPTIONAL SETTINGS (press Enter to use defaults)")
    print("-"*80)

    # Ask for depth limit
    while True:
        depth_input = input("Max crawl depth (default: 999): ").strip()
        if not depth_input:
            max_depth = 999
            break
        try:
            max_depth = int(depth_input)
            if max_depth < 1:
                print("❌ Depth must be at least 1. Try again.")
                continue
            break
        except ValueError:
            print("❌ Please enter a valid number.")
            continue

    # Ask for report
    generate_report = input("Generate report after update? (y/n, default: n): ").strip().lower() in ['y', 'yes']

    # Ask for sitemap
    sitemap_url = input("Sitemap URL (optional, press Enter to skip): ").strip()
    if sitemap_url and not sitemap_url.startswith(('http://', 'https://')):
        sitemap_url = 'https://' + sitemap_url

    return {
        'max_depth': max_depth,
        'generate_report': generate_report,
        'sitemap_url': sitemap_url if sitemap_url else None
    }


def run_update(domain, start_url, options):
    """Execute the update"""
    from updater import run_updater

    print("\n" + "="*80)
    print("🚀 STARTING UPDATE")
    print("="*80)
    print(f"Domain: {domain}")
    print(f"Start URL: {start_url}")
    print(f"Max Depth: {options['max_depth']}")
    if options['sitemap_url']:
        print(f"Sitemap: {options['sitemap_url']}")
    print(f"Generate Report: {'Yes' if options['generate_report'] else 'No'}")
    print("="*80 + "\n")

    start_time = datetime.now()

    try:
        # Run the updater
        run_updater(
            domain=domain,
            start_url=start_url,
            mongo_uri=None,  # Uses config.py default
            max_depth=options['max_depth'],
            sitemap_url=options['sitemap_url']
        )

        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "="*80)
        print("✅ UPDATE COMPLETED SUCCESSFULLY")
        print("="*80)
        print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration}")
        print("="*80 + "\n")

        # Generate report if requested
        if options['generate_report']:
            print("\n📊 Generating update report...\n")
            try:
                from report_generator import UpdateReportGenerator
                generator = UpdateReportGenerator()
                generator.generate_full_report()
                generator.close()
            except Exception as e:
                logger.error(f"Failed to generate report: {e}")

        return True

    except KeyboardInterrupt:
        print("\n\n🛑 Update cancelled by user (Ctrl+C)")
        return False
    except Exception as e:
        logger.error(f"\n❌ Update failed: {e}", exc_info=True)
        return False


def main():
    """Main entry point"""
    print_banner()

    # Get URL from user
    domain, start_url = get_user_input()

    # Get optional settings
    options = ask_options()

    # Confirm and start
    print("\n" + "="*80)
    print("Press Ctrl+C at any time to stop the update")
    print("="*80)
    input("\nPress Enter to start the update...")

    # Run update
    success = run_update(domain, start_url, options)

    if success:
        print("\n✅ All operations completed successfully")
        print("\nRun again? Just type: python run_updater.py\n")
    else:
        print("\n❌ Operation failed or was cancelled\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Exiting...\n")
        sys.exit(0)
