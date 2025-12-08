"""
URL Content Scraper
Supports two modes:
1. Basic: requests + BeautifulSoup (lightweight, default)
2. Advanced: Playwright (for JS-heavy sites, requires premium server)
"""
import re
import logging
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
MAX_CONTENT_LENGTH = 30000
REQUEST_TIMEOUT = 15
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'

# Check if Playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


def clean_text(text: str) -> str:
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def scrape_url(url: str, mode: str = 'basic') -> dict:
    """
    Scrape content from URL.
    
    Args:
        url: The URL to scrape
        mode: 'basic' (requests+BeautifulSoup) or 'advanced' (Playwright)
        
    Returns:
        dict with success, title, content, source_url, or error
    """
    if mode == 'advanced':
        return scrape_url_advanced(url)
    return scrape_url_basic(url)


def scrape_url_basic(url: str) -> dict:
    """Basic scraping using requests + BeautifulSoup. Fast but no JS support."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return {'success': False, 'error': 'Only HTTP/HTTPS supported'}
        
        resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        for el in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            el.decompose()
        
        title = clean_text(soup.title.string) if soup.title else 'Imported'
        
        # Find main content
        content = ''
        for sel in ['main', 'article', '.content', '#content', '.post', '.entry']:
            el = soup.select_one(sel)
            if el:
                content = clean_text(el.get_text('\n'))
                if len(content) > 100:
                    break
        
        if not content and soup.body:
            content = clean_text(soup.body.get_text('\n'))
        
        if len(content) < 50:
            return {'success': False, 'error': 'No meaningful content found. Try Advanced mode for JS-heavy sites.'}
        
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + '\n[truncated]'
        
        return {'success': True, 'title': title[:200], 'content': content, 'source_url': url, 'mode': 'basic'}
        
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Request timed out'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Request failed: {str(e)[:80]}'}
    except Exception as e:
        return {'success': False, 'error': str(e)[:100]}


def scrape_url_advanced(url: str) -> dict:
    """
    Advanced scraping using Playwright. Supports JS-heavy sites.
    Requires Playwright to be installed: pip install playwright && playwright install chromium
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {
            'success': False, 
            'error': 'Advanced scraping not available. Playwright not installed. Use Basic mode or upgrade server.'
        }
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return {'success': False, 'error': 'Only HTTP/HTTPS supported'}
        
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()
            
            # Navigate and wait for content
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait a bit for dynamic content
            page.wait_for_timeout(2000)
            
            # Get title
            title = page.title() or 'Imported'
            
            # Try to get main content
            content = ''
            
            # Try common content selectors
            selectors = ['main', 'article', '.content', '#content', '.post', '.entry', '[role="main"]']
            for sel in selectors:
                try:
                    el = page.query_selector(sel)
                    if el:
                        content = clean_text(el.inner_text())
                        if len(content) > 100:
                            break
                except:
                    continue
            
            # Fallback to body
            if not content or len(content) < 50:
                body = page.query_selector('body')
                if body:
                    content = clean_text(body.inner_text())
            
            browser.close()
        
        if len(content) < 50:
            return {'success': False, 'error': 'No meaningful content found'}
        
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + '\n[truncated]'
        
        return {'success': True, 'title': title[:200], 'content': content, 'source_url': url, 'mode': 'advanced'}
        
    except Exception as e:
        logger.error(f"Playwright scraping error: {str(e)}")
        return {'success': False, 'error': f'Advanced scraping failed: {str(e)[:80]}'}


def summarize_content(content: str, title: str = '') -> str:
    """
    Summarize/truncate content to a reasonable size for memory storage.
    This is a simple extraction-based summary, not AI-powered.
    """
    if not content:
        return ''
    
    # If content is already short enough, return as-is
    if len(content) <= 2000:
        return content
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
    
    if not paragraphs:
        return content[:2000] + '\n[truncated]'
    
    # Take first few paragraphs that fit within limit
    summary_parts = []
    total_length = 0
    max_length = 2000
    
    for para in paragraphs:
        if total_length + len(para) > max_length:
            # Add partial paragraph if we have room
            remaining = max_length - total_length
            if remaining > 100:
                summary_parts.append(para[:remaining] + '...')
            break
        summary_parts.append(para)
        total_length += len(para) + 1
    
    if not summary_parts:
        return content[:2000] + '\n[truncated]'
    
    result = '\n\n'.join(summary_parts)
    
    # Add note if truncated
    if len(content) > len(result):
        result += f'\n\n[Content truncated from {len(content)} to {len(result)} characters]'
    
    return result
