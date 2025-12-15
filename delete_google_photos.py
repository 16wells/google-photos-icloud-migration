#!/usr/bin/env python3
"""
Script to delete all photos and videos from a Google Photos account.

This script uses browser automation to interact with the Google Photos web interface
since the Google Photos API does not support deletion operations.

WARNING: This will permanently delete all photos and videos from your Google Photos account.
Make sure you have a complete backup before running this script.
"""

import argparse
import logging
import time
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_photos_deletion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

console = Console()


class GooglePhotosDeleter:
    """Handles deletion of photos and videos from Google Photos."""
    
    def __init__(self, headless: bool = False, dry_run: bool = True, browser: str = "chrome"):
        """
        Initialize the Google Photos deleter.
        
        Args:
            headless: Run browser in headless mode (no visible window) - Chrome only
            dry_run: If True, only plan what would be deleted without actually deleting
            browser: Browser to use ("chrome" or "safari")
        """
        self.headless = headless
        self.dry_run = dry_run
        self.browser = browser.lower()
        self.driver: Optional[webdriver.Chrome] = None
        self.deleted_count = 0
        self.failed_count = 0
        self.start_time = None
        
        # Safari doesn't support headless mode
        if self.browser == "safari" and self.headless:
            logger.warning("Safari doesn't support headless mode. Running in visible mode.")
            self.headless = False
        
    def _setup_driver(self):
        """Set up WebDriver with appropriate options for the selected browser."""
        if self.browser == "safari":
            self._setup_safari_driver()
        else:
            self._setup_chrome_driver()
    
    def _setup_safari_driver(self):
        """Set up Safari WebDriver."""
        try:
            self.driver = webdriver.Safari()
            logger.info("Safari WebDriver initialized successfully")
            # Set window size for better element visibility
            self.driver.set_window_size(1920, 1080)
        except Exception as e:
            logger.error(f"Failed to initialize Safari driver: {e}")
            logger.error("\nSafari WebDriver setup required:")
            logger.error("1. Enable Develop menu: Safari > Preferences > Advanced > Show Develop menu")
            logger.error("2. Enable Remote Automation: Develop > Allow Remote Automation")
            logger.error("3. Authorize safaridriver:")
            logger.error("   Try: /usr/bin/safaridriver --enable")
            logger.error("   Or:  sudo /usr/bin/safaridriver --enable")
            logger.error("   (Enter your macOS user account password when prompted)")
            logger.error("   If password fails, check System Settings > Privacy & Security")
            raise
    
    def _setup_chrome_driver(self):
        """Set up Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Try to use webdriver-manager first (automatic ChromeDriver management)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("ChromeDriver automatically downloaded and configured via webdriver-manager")
        except ImportError:
            # Fallback to system ChromeDriver if webdriver-manager not available
            logger.info("webdriver-manager not available, using system ChromeDriver")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver: {e}")
                logger.error("Please install dependencies:")
                logger.error("  pip install webdriver-manager")
                logger.error("Or manually install ChromeDriver from:")
                logger.error("  https://googlechromelabs.github.io/chrome-for-testing/")
                logger.error("  (Note: Homebrew chromedriver is deprecated)")
                raise
        except Exception as e:
            # If webdriver-manager fails, try system ChromeDriver
            logger.warning(f"webdriver-manager failed: {e}, trying system ChromeDriver")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as e2:
                logger.error(f"Failed to initialize Chrome driver: {e2}")
                logger.error("Please install dependencies:")
                logger.error("  pip install webdriver-manager")
                logger.error("Or manually install ChromeDriver from:")
                logger.error("  https://googlechromelabs.github.io/chrome-for-testing/")
                raise
        
        # Set window size for better element visibility
        self.driver.set_window_size(1920, 1080)
        
    
    def _wait_for_element(self, by: By, value: str, timeout: int = 10):
        """Wait for an element to be present and visible."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.warning(f"Element not found: {by}={value}")
            return None
    
    def _wait_for_clickable(self, by: By, value: str, timeout: int = 10):
        """Wait for an element to be clickable."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            logger.warning(f"Element not clickable: {by}={value}")
            return None
    
    def login(self) -> bool:
        """
        Navigate to Google Photos and wait for user to log in manually.
        
        Returns:
            True if login appears successful, False otherwise
        """
        logger.info("Opening Google Photos...")
        self.driver.get("https://photos.google.com")
        
        console.print("\n[bold yellow]⚠️  MANUAL LOGIN REQUIRED[/bold yellow]")
        console.print("Please log in to your Google account in the browser window.")
        console.print("Once you're logged in and can see your photos, press Enter here to continue...")
        
        input()
        
        # Check if we're on the photos page or redirected to promo/about page
        time.sleep(2)
        current_url = self.driver.current_url
        
        # Handle redirect to promo/about page
        if "photos.google.com/about" in current_url or "google.com/photos/about" in current_url:
            logger.info("Detected redirect to promo page, navigating to photos page...")
            # Try to navigate directly to the photos page
            # The /u/1/ path is for the logged-in user's photos
            self.driver.get("https://photos.google.com/u/1/")
            time.sleep(3)
            current_url = self.driver.current_url
        
        # Also try to dismiss any promo overlays or modals
        try:
            # Look for common dismiss buttons (X, Close, Skip, etc.)
            dismiss_selectors = [
                "button[aria-label*='Close']",
                "button[aria-label*='close']",
                "button[aria-label*='Dismiss']",
                "button[aria-label*='dismiss']",
                "button[aria-label*='Skip']",
                "button[aria-label*='skip']",
                "[role='button'][aria-label*='Close']",
                ".close-button",
                "[data-dismiss]",
            ]
            
            for selector in dismiss_selectors:
                try:
                    dismiss_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if dismiss_btn.is_displayed():
                        dismiss_btn.click()
                        logger.info("Dismissed promo overlay")
                        time.sleep(1)
                        break
                except (NoSuchElementException, ElementClickInterceptedException):
                    continue
        except Exception as e:
            logger.debug(f"Could not dismiss promo overlay: {e}")
        
        # Final check - navigate directly if still not on photos page
        if "photos.google.com" not in current_url or "about" in current_url:
            logger.info("Navigating directly to photos page...")
            self.driver.get("https://photos.google.com/u/1/")
            time.sleep(3)
            current_url = self.driver.current_url
        
        if "photos.google.com" in current_url and "about" not in current_url:
            logger.info(f"Successfully navigated to Google Photos: {current_url}")
            return True
        else:
            logger.warning(f"Still on unexpected URL: {current_url}")
            logger.warning("You may need to manually navigate to https://photos.google.com/u/1/ in the browser")
            return True  # Still return True to allow user to proceed
    
    def _select_all_photos(self) -> bool:
        """
        Select all photos on the current page.
        
        Returns:
            True if selection was successful
        """
        try:
            # Try keyboard shortcut to select all
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.COMMAND + "a")  # macOS
            time.sleep(1)
            
            # Also try Ctrl+A for Windows/Linux compatibility
            body.send_keys(Keys.CONTROL + "a")
            time.sleep(1)
            
            logger.debug("Attempted to select all photos using keyboard shortcut")
            return True
        except Exception as e:
            logger.warning(f"Failed to select all photos: {e}")
            return False
    
    def _click_delete_button(self) -> bool:
        """
        Click the delete button in the toolbar.
        
        Returns:
            True if delete button was clicked successfully
        """
        # Try multiple possible selectors for the delete button
        delete_selectors = [
            "button[aria-label*='Delete']",
            "button[aria-label*='delete']",
            "button[data-tooltip*='Delete']",
            "button[data-tooltip*='delete']",
            "div[aria-label*='Delete']",
            "div[data-tooltip*='Delete']",
            "[aria-label='Delete']",
            "[data-tooltip='Delete']",
        ]
        
        for selector in delete_selectors:
            try:
                delete_btn = self._wait_for_clickable(By.CSS_SELECTOR, selector, timeout=3)
                if delete_btn:
                    delete_btn.click()
                    logger.debug(f"Clicked delete button using selector: {selector}")
                    time.sleep(1)
                    return True
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        logger.warning("Could not find delete button")
        return False
    
    def _confirm_deletion(self) -> bool:
        """
        Confirm the deletion in the dialog.
        
        Returns:
            True if confirmation was successful
        """
        # Wait for confirmation dialog
        time.sleep(2)
        
        # Try to find and click confirm button
        confirm_selectors = [
            "button[aria-label*='Delete']",
            "button:contains('Delete')",
            "button:contains('Move to trash')",
            "button:contains('Move to Trash')",
            "[role='button']:contains('Delete')",
        ]
        
        # Also try to find by text content
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                text = button.text.lower()
                if "delete" in text or "trash" in text:
                    if "cancel" not in text and "undo" not in text:
                        button.click()
                        logger.debug("Clicked confirm button by text")
                        time.sleep(2)
                        return True
        except Exception as e:
            logger.debug(f"Failed to find confirm button by text: {e}")
        
        # Try keyboard Enter as fallback
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.RETURN)
            time.sleep(2)
            logger.debug("Sent Enter key to confirm deletion")
            return True
        except Exception as e:
            logger.warning(f"Failed to confirm deletion: {e}")
            return False
    
    def _get_photo_count(self) -> int:
        """
        Try to get an estimate of total photos.
        
        Returns:
            Estimated number of photos, or -1 if unable to determine
        """
        try:
            # Look for photo count indicators in the UI
            # This is approximate and may not be accurate
            photo_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "img[data-loaded='true'], div[data-item-id], div[role='gridcell']"
            )
            return len(photo_elements)
        except Exception:
            return -1
    
    def delete_all_photos(self, batch_size: int = 50, delay: float = 2.0) -> dict:
        """
        Delete all photos and videos from Google Photos.
        
        Args:
            batch_size: Number of items to delete per batch
            delay: Delay between operations in seconds
        
        Returns:
            Dictionary with deletion statistics
        """
        if self.dry_run:
            console.print("\n[bold yellow]🔍 DRY RUN MODE - No photos will actually be deleted[/bold yellow]")
        
        self.start_time = datetime.now()
        stats = {
            'total_deleted': 0,
            'total_failed': 0,
            'batches_processed': 0,
            'start_time': self.start_time,
            'end_time': None
        }
        
        console.print("\n[bold]Starting deletion process...[/bold]")
        
        # Scroll to top first
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        batch_num = 0
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]Processing batches...", total=None)
            
            while consecutive_failures < max_consecutive_failures:
                batch_num += 1
                progress.update(task, description=f"[cyan]Batch {batch_num}...")
                
                # Scroll to load more photos
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Scroll back up a bit to ensure we're selecting from the top
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                # Select all photos
                if not self._select_all_photos():
                    consecutive_failures += 1
                    logger.warning(f"Failed to select photos in batch {batch_num}")
                    time.sleep(delay)
                    continue
                
                time.sleep(1)
                
                # Check if anything is selected
                try:
                    # Look for selection indicators
                    selected = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "[aria-selected='true'], [data-selected='true'], .selected"
                    )
                    if not selected and batch_num > 1:
                        logger.info("No more photos to select. Deletion complete.")
                        break
                except Exception:
                    pass
                
                if self.dry_run:
                    # In dry run, just count what would be deleted
                    estimated = self._get_photo_count()
                    if estimated > 0:
                        stats['total_deleted'] += min(estimated, batch_size)
                        stats['batches_processed'] += 1
                        logger.info(f"[DRY RUN] Would delete batch {batch_num} (~{min(estimated, batch_size)} items)")
                    time.sleep(delay)
                    continue
                
                # Click delete button
                if not self._click_delete_button():
                    consecutive_failures += 1
                    logger.warning(f"Failed to click delete button in batch {batch_num}")
                    time.sleep(delay)
                    continue
                
                # Confirm deletion
                if not self._confirm_deletion():
                    consecutive_failures += 1
                    logger.warning(f"Failed to confirm deletion in batch {batch_num}")
                    time.sleep(delay)
                    continue
                
                # Success
                consecutive_failures = 0
                stats['total_deleted'] += batch_size  # Approximate
                stats['batches_processed'] += 1
                self.deleted_count += batch_size
                
                logger.info(f"Deleted batch {batch_num} (~{batch_size} items)")
                
                # Wait before next batch
                time.sleep(delay)
                
                # Check if we're done (no more photos visible)
                try:
                    photos = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "img[data-loaded='true'], div[data-item-id]"
                    )
                    if len(photos) == 0:
                        logger.info("No more photos found. Deletion complete.")
                        break
                except Exception:
                    pass
        
        stats['end_time'] = datetime.now()
        stats['total_failed'] = self.failed_count
        
        return stats
    
    def create_deletion_plan(self) -> dict:
        """
        Create a plan of what would be deleted (dry run).
        
        Returns:
            Dictionary with plan information
        """
        console.print("\n[bold cyan]📋 Creating deletion plan...[/bold cyan]")
        
        # Scroll through photos to get an estimate
        console.print("Scanning photos...")
        
        scrolls = 0
        max_scrolls = 20  # Limit scanning to avoid infinite scroll
        
        while scrolls < max_scrolls:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            scrolls += 1
            
            # Check if we've reached the bottom
            scroll_height = self.driver.execute_script("return document.body.scrollHeight;")
            window_height = self.driver.execute_script("return window.innerHeight;")
            scroll_position = self.driver.execute_script("return window.pageYOffset;")
            
            if scroll_position + window_height >= scroll_height - 100:
                # Reached bottom
                break
        
        # Get estimate
        estimated_count = self._get_photo_count()
        
        plan = {
            'estimated_photos': estimated_count,
            'account_url': self.driver.current_url,
            'scan_time': datetime.now().isoformat(),
            'scrolls_performed': scrolls
        }
        
        return plan
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def print_plan(plan: dict):
    """Print the deletion plan in a formatted table."""
    table = Table(title="Deletion Plan", show_header=True, header_style="bold magenta")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Estimated Photos/Videos", f"{plan['estimated_photos']:,}" if plan['estimated_photos'] > 0 else "Unable to determine")
    table.add_row("Account URL", plan['account_url'])
    table.add_row("Scan Time", plan['scan_time'])
    table.add_row("Scrolls Performed", str(plan['scrolls_performed']))
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def print_stats(stats: dict, dry_run: bool):
    """Print deletion statistics."""
    table = Table(
        title="Deletion Statistics" if not dry_run else "Dry Run Results",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    duration = (stats['end_time'] - stats['start_time']).total_seconds()
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    
    table.add_row("Items Deleted" if not dry_run else "Items That Would Be Deleted", 
                 f"{stats['total_deleted']:,}")
    table.add_row("Batches Processed", str(stats['batches_processed']))
    table.add_row("Failed Operations", str(stats['total_failed']))
    table.add_row("Duration", f"{hours}h {minutes}m {seconds}s")
    table.add_row("Start Time", stats['start_time'].strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("End Time", stats['end_time'].strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Delete all photos and videos from Google Photos account",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WARNING: This script will permanently delete all photos and videos from your Google Photos account.
Make sure you have a complete backup before running this script.

Examples:
  # Dry run (plan only, no deletion):
  python delete_google_photos.py --dry-run
  
  # Actually delete (after reviewing plan):
  python delete_google_photos.py --execute
  
  # Use Safari instead of Chrome:
  python delete_google_photos.py --execute --browser safari
  
  # Headless mode (Chrome only, no browser window):
  python delete_google_photos.py --execute --headless
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Dry run mode: plan what would be deleted without actually deleting (default)'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete photos (overrides --dry-run). Use with caution!'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window) - Chrome only, Safari doesn\'t support headless'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of items to delete per batch (default: 50)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between operations in seconds (default: 2.0)'
    )
    
    parser.add_argument(
        '--browser',
        type=str,
        choices=['chrome', 'safari'],
        default='chrome',
        help='Browser to use: chrome or safari (default: chrome)'
    )
    
    args = parser.parse_args()
    
    # Determine if this is a dry run
    dry_run = not args.execute
    
    # Safety check
    if not dry_run:
        console.print("\n[bold red]⚠️  WARNING: EXECUTION MODE[/bold red]")
        console.print("[bold red]This will PERMANENTLY DELETE all photos and videos from your Google Photos account![/bold red]\n")
        
        confirmation = input("Type 'DELETE ALL PHOTOS' to confirm: ")
        if confirmation != "DELETE ALL PHOTOS":
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return
        
        console.print("\n[bold yellow]Final confirmation required...[/bold yellow]")
        console.print("This action cannot be undone. Are you absolutely sure?")
        final_confirmation = input("Type 'YES I AM SURE' to proceed: ")
        if final_confirmation != "YES I AM SURE":
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return
    
    # Create deleter
    deleter = GooglePhotosDeleter(headless=args.headless, dry_run=dry_run, browser=args.browser)
    
    try:
        # Setup driver
        deleter._setup_driver()
        
        # Login
        if not deleter.login():
            console.print("[red]Failed to access Google Photos. Please check your login.[/red]")
            return
        
        # Create and show plan
        plan = deleter.create_deletion_plan()
        print_plan(plan)
        
        if dry_run:
            console.print("[yellow]This was a dry run. No photos were deleted.[/yellow]")
            console.print("[yellow]To actually delete photos, run with --execute flag.[/yellow]")
        else:
            # Proceed with deletion
            console.print("[bold red]Starting actual deletion...[/bold red]")
            time.sleep(3)  # Give user a moment to see the warning
            
            stats = deleter.delete_all_photos(
                batch_size=args.batch_size,
                delay=args.delay
            )
            
            print_stats(stats, dry_run=False)
            console.print("[green]✓ Deletion process completed![/green]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Deletion interrupted by user.[/yellow]")
        logger.info("Deletion interrupted by user")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("Error during deletion process")
    finally:
        deleter.close()


if __name__ == "__main__":
    main()

