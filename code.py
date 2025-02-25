from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os
import logging
import time
from urllib.parse import urljoin, urlparse
import pdfkit

# Constants
OUTPUT_DIR_BASE = "maplestoryworlds_docs_selenium"
PDF_OPTIONS = {
    'encoding': "UTF-8",
    '--disable-smart-shrinking': '',
    '--load-error-handling': 'ignore',
    '--load-media-error-handling': 'ignore',
    '--javascript-delay': '5000',
    '--user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"
}
CHROME_BINARY_LOCATION = "C:/Program Files/Google/Chrome/Application/chrome.exe"
WKHTMLTOPDF_PATH = 'C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe'

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler("scraping_selenium.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# PDF generation configuration
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)


def fetch_page_content_with_selenium(url, wait_time=5):
    """Fetches HTML content using Selenium, handling JavaScript rendering."""
    try:
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.binary_location = CHROME_BINARY_LOCATION

        driver.get(url)
        time.sleep(wait_time)

        html = driver.page_source
        return BeautifulSoup(html, 'html.parser')

    except Exception as e:
        logging.exception(f"Error fetching {url} with Selenium: {e}")
        return None


def save_as_pdf(url, filename):
    """Saves the given URL as a PDF file."""
    try:
        pdfkit.from_url(url, filename, configuration=config, options=PDF_OPTIONS)
        logging.info(f"Saved as PDF: {filename}")
    except Exception as e:  # More specific exception handling if possible
        logging.error(f"Error saving PDF {filename}: {e}")



def save_as_text(content, filename):
    """Extracts text from HTML and saves it to a .txt file."""
    try:
        if isinstance(content, str):
            soup = BeautifulSoup(content, 'html.parser')
        else:
            soup = content

        text_content = soup.get_text(separator='\n', strip=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text_content)
        logging.info(f"Saved as text: {filename}")
    except Exception as e:
        logging.error(f"Error saving as text: {e}")


def get_filename_from_url(url):
    """Generates a filename from the URL's path."""
    parsed_url = urlparse(url)
    filename = parsed_url.path.split('/')[-1]
    if not filename:  # Use a default if the URL path ends with '/'
        filename = "index"
    return "".join(c if c.isalnum() else "_" for c in filename)



def scrape_page_content(url, output_dir):
    """Scrapes content from a single page and saves it as PDF and TXT."""
    soup = fetch_page_content_with_selenium(url)
    if not soup:
        return

    # Title extraction (improved CSS selectors)
    title_selector = "h1, h2, h3, .post-title, .article-header .title-text, #content-title"
    title_tag = soup.select_one(title_selector)
    title = title_tag.get_text(strip=True) if title_tag else None


    if not title:
        title = get_filename_from_url(url)
        logging.warning(f"No title found for {url}, using URL for filename: {title}")


    # Content extraction
    content_selectors = ['.markdown-body', '.wrap_body', '.article-content']
    content = None
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            break

    if not content:
        content = soup  # Fallback: Use the entire soup if no specific content div is found
        logging.warning(f"No specific content div found in {url}, using entire soup.")

    cleaned_title = "".join(c if c.isalnum() else "_" for c in title)
    filename_base = os.path.join(output_dir, cleaned_title)

    save_as_pdf(url, f"{filename_base}.pdf")
    save_as_text(content.prettify() if content else str(soup), f"{filename_base}.txt")



def scrape_and_save_pages_from_links(base_url, output_dir_base, link_selector, dir_name):
    """Finds links using the given selector and scrapes each linked page."""
    soup = fetch_page_content_with_selenium(base_url)
    if not soup:
        return

    output_dir = os.path.join(output_dir_base, dir_name)
    os.makedirs(output_dir, exist_ok=True)

    links = soup.select(link_selector)
    logging.info(f"Found {len(links)} links with selector '{link_selector}' at {base_url}")

    for link in links:
        href = link.get('href')
        if href:
            absolute_url = urljoin(base_url, href)
            scrape_page_content(absolute_url, output_dir)


def extract_mayi_titles_and_links(base_url):
    """Extracts titles and links from the May-I article page."""
    soup = fetch_page_content_with_selenium(base_url)
    if not soup:
        return []

    titles_and_links = []
    article_items = soup.select('.article-list > .article-item > a')
    for item in article_items:
        title_element = item.select_one('.title')
        href = item.get('href')
        if title_element and href:
            title = title_element.get_text(strip=True)
            absolute_url = urljoin(base_url, href)
            titles_and_links.append((title, absolute_url))
    return titles_and_links


def scrape_and_save_mayi_articles(base_url, output_dir_base):
    """Scrapes May-I articles based on titles and links."""
    titles_and_links = extract_mayi_titles_and_links(base_url)
    output_dir = os.path.join(output_dir_base, "mayi_articles")
    os.makedirs(output_dir, exist_ok=True)

    for title, url in titles_and_links:
        soup = fetch_page_content_with_selenium(url)
        if soup:
            content = soup.select_one('.article-content')
            if content:
                scrape_page_content(url, output_dir) # 함수 사용
            else:
                logging.warning(f"Skipping May-I article (no content found): {title} ({url})")
        else:
            logging.warning(f"Could not fetch May-I article page: {title} ({url})")


# ChromeDriverManager().install() 한 번만 호출
service = ChromeService(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=ChromeOptions())


def main():
    """Main function to orchestrate the scraping process."""

    # Docs page scraping
    base_url_docs = "https://maplestoryworlds-creators.nexon.com/ko/docs"
    scrape_and_save_pages_from_links(base_url_docs, OUTPUT_DIR_BASE, 'a[href*="postId="]', "docs")

    # May-I articles scraping (title-based)
    base_url_mayi = "https://maplestoryworlds-creators.nexon.com/ko/resource/may-i-article"
    scrape_and_save_mayi_articles(base_url_mayi, OUTPUT_DIR_BASE)

    # API Reference page scraping
    base_url_api = "https://maplestoryworlds-creators.nexon.com/ko/apiReference/How-to-use-API-Reference"
    scrape_and_save_pages_from_links(base_url_api, OUTPUT_DIR_BASE, 'a[href*="/ko/apiReference/"]', "apiReference")

    driver.quit()

if __name__ == "__main__":
    main()
