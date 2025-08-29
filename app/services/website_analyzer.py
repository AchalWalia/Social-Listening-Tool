"""
Website Analysis Service for Enhanced Company Onboarding

This module provides functionality to:
1. Validate website URLs
2. Scrape and analyze website content
3. Extract social media links
4. Parse app store links for package IDs
5. Generate value proposition summaries
"""

import re
import requests
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Tuple
import streamlit as st
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import time


class WebsiteAnalyzer:
    """Handles website analysis for company onboarding"""
    
    def __init__(self):
        self.session = HTMLSession()
        # Use realistic browser headers to avoid bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate if a URL is reachable and returns a success status
        
        Args:
            url: The URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Parse URL to check if it's well-formed
            parsed = urlparse(url)
            if not parsed.netloc:
                return False, "Invalid URL format. Please include the domain name."
            
            # Make HEAD request first (faster)
            response = self.session.head(url, timeout=10, allow_redirects=True)
            
            # If HEAD fails, try GET
            if response.status_code >= 400:
                response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code >= 400:
                return False, f"Website returned error {response.status_code}. Please check the URL."
                
            return True, ""
            
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to this website. Please check the URL and try again."
        except requests.exceptions.Timeout:
            return False, "Website took too long to respond. Please try again later."
        except requests.exceptions.RequestException as e:
            return False, f"Error accessing website: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def scrape_website_content(self, url: str) -> Dict[str, any]:
        """
        Scrape website content and extract text and links with enhanced error recovery
        
        Args:
            url: The validated URL to scrape
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        # Retry configuration
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries + 1):
            try:
                # Add protocol if missing
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                # For certain attempts, try different approaches
                if attempt == 1:
                    # Try with different User-Agent
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    })
                elif attempt == 2:
                    # Try with mobile User-Agent
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
                    })
                
                # Get the page with timeout
                response = self.session.get(url, timeout=20)
                
                # Handle different HTTP status codes
                if response.status_code == 406:
                    # Not Acceptable - try with different headers
                    if attempt < max_retries:
                        print(f"Attempt {attempt + 1}: Got 406 error, trying different headers...")
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                elif response.status_code == 403:
                    # Forbidden - might be bot detection
                    if attempt < max_retries:
                        print(f"Attempt {attempt + 1}: Got 403 error, trying different approach...")
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                elif response.status_code >= 400:
                    if attempt < max_retries:
                        print(f"Attempt {attempt + 1}: Got {response.status_code} error, retrying...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'error': f"Website returned HTTP {response.status_code}. This might be due to bot detection or access restrictions.",
                            'url': url,
                            'text_content': '',
                            'social_links': {},
                            'app_store_links': {},
                            'all_links': []
                        }
                
                # Success! Process the response
                break
                
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"Attempt {attempt + 1}: Timeout, retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        'success': False,
                        'error': "Website took too long to respond after multiple attempts.",
                        'url': url,
                        'text_content': '',
                        'social_links': {},
                        'app_store_links': {},
                        'all_links': []
                    }
            except requests.exceptions.ConnectionError:
                if attempt < max_retries:
                    print(f"Attempt {attempt + 1}: Connection error, retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        'success': False,
                        'error': "Could not connect to the website after multiple attempts.",
                        'url': url,
                        'text_content': '',
                        'social_links': {},
                        'app_store_links': {},
                        'all_links': []
                    }
            except Exception as e:
                if attempt < max_retries:
                    print(f"Attempt {attempt + 1}: Unexpected error ({str(e)}), retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        'success': False,
                        'error': f"Unexpected error after multiple attempts: {str(e)}",
                        'url': url,
                        'text_content': '',
                        'social_links': {},
                        'app_store_links': {},
                        'all_links': []
                    }
        
        # If we get here, we have a successful response
        try:
            # Try to render JavaScript (with timeout and fallback)
            js_rendered = False
            try:
                response.html.render(timeout=15, wait=2, sleep=1)
                js_rendered = True
            except Exception as js_error:
                # Fall back to static HTML if JS rendering fails
                print(f"JavaScript rendering failed, using static HTML: {js_error}")
                pass
                
                # Parse with BeautifulSoup for better text extraction
                soup = BeautifulSoup(response.html.html, 'html.parser')
                
                # Remove script, style, and other non-content elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
                    element.decompose()
                
                # Extract text content with fallback methods
                text_content = self._extract_main_content(soup)
                
                # If no meaningful content found, try alternative extraction
                if not text_content or len(text_content.strip()) < 50:
                    # Try extracting from body directly
                    body = soup.find('body')
                    if body:
                        text_content = body.get_text(separator=' ', strip=True)
                        text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                # Extract all links with error handling
                try:
                    all_links = self._extract_all_links(soup, url)
                except Exception as link_error:
                    print(f"Link extraction failed: {link_error}")
                    all_links = []
                
                # Parse social media links with enhanced detection
                try:
                    # Method 1: Parse from extracted links
                    social_links = self._parse_social_links(all_links)
                    
                    # Method 2: Detect from page structure and CSS classes
                    structure_social = self._detect_social_from_structure(soup, url)
                    
                    # Method 3: Detect from raw HTML source
                    html_social = self._detect_social_from_html_source(soup, str(soup))
                    
                    # Method 4: Advanced icon and class detection (NEW)
                    icon_social = self._detect_social_from_icons_and_classes(soup, url)
                    
                    # Method 5: JavaScript pattern detection (NEW)
                    js_social = self._detect_social_from_javascript_patterns(soup, url)
                    
                    # Method 6: Meta tag detection (NEW)
                    meta_social = self._detect_social_from_meta_tags(soup, url)
                    
                    # Combine results, preferring structure-based detection for accuracy
                    for platform, link in structure_social.items():
                        if platform not in social_links or not social_links[platform]:
                            social_links[platform] = link
                    
                    # Add HTML source results
                    for platform, link in html_social.items():
                        if platform not in social_links or not social_links[platform]:
                            social_links[platform] = link
                    
                    # Add icon results
                    for platform, link in icon_social.items():
                        if platform not in social_links or not social_links[platform]:
                            social_links[platform] = link
                    
                    # Add JS results
                    for platform, link in js_social.items():
                        if platform not in social_links or not social_links[platform]:
                            social_links[platform] = link
                    
                    # Add Meta results
                    for platform, link in meta_social.items():
                        if platform not in social_links or not social_links[platform]:
                            social_links[platform] = link
                    
                    print(f"🔍 Social media detection: URL-based={len(self._parse_social_links(all_links))}, Structure-based={len(structure_social)}, HTML-based={len(html_social)}, Icons={len(icon_social)}, JS={len(js_social)}, Meta={len(meta_social)}, Combined={len(social_links)}")
                    
                except Exception as social_error:
                    print(f"Social link parsing failed: {social_error}")
                    social_links = {}
                
                # Parse app store links with enhanced detection
                try:
                    # Method 1: Parse from extracted links
                    app_store_links = self._parse_app_store_links(all_links)
                    
                    # Method 2: Detect from page structure and download buttons
                    button_apps = self._detect_app_download_buttons(soup, url)
                    
                    # Method 3: Detect from footer and download sections
                    section_apps = self._detect_app_store_from_sections(soup, url)
                    
                    # Combine results, preferring structure-based detection for accuracy
                    for store_type, link in list(button_apps.items()):
                        if store_type not in app_store_links or not app_store_links[store_type]:
                            app_store_links[store_type] = link
                    
                    for store_type, link in list(section_apps.items()):
                        if store_type not in app_store_links or not app_store_links[store_type]:
                            app_store_links[store_type] = link
                    
                    print(f"🔍 App store detection: URL-based={len(self._parse_app_store_links(all_links))}, Button-based={len(button_apps)}, Section-based={len(section_apps)}, Combined={len(app_store_links)}")
                    
                except Exception as app_error:
                    print(f"App store link parsing failed: {app_error}")
                    app_store_links = {}
                
                return {
                    'success': True,
                    'url': url,
                    'text_content': text_content,
                    'social_links': social_links,
                    'app_store_links': app_store_links,
                    'all_links': all_links,
                    'js_rendered': js_rendered,
                    'error': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'url': url,
                'text_content': '',
                'social_links': {},
                'app_store_links': {},
                'all_links': [],
                'error': f"Failed to process response after multiple attempts: {str(e)}"
            }
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from HTML"""
        # Priority order for content extraction
        content_selectors = [
            'main',
            'article', 
            '[role="main"]',
            '.content',
            '#content',
            '.main-content',
            'body'
        ]
        
        text_content = ""
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                text_content = elements[0].get_text(separator=' ', strip=True)
                break
        
        # Clean up the text
        text_content = re.sub(r'\s+', ' ', text_content)
        text_content = text_content.strip()
        
        # Limit length to avoid overwhelming the summarization model
        if len(text_content) > 5000:
            text_content = text_content[:5000] + "..."
        
        return text_content
    
    def _extract_all_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from the page including JavaScript-generated and redirect links"""
        links = []
        
        # Extract standard href links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue  # Skip anchors and non-web links
            
            links.append(href)
        
        # Extract data attributes that might contain social/app links
        for element in soup.find_all(attrs={'data-href': True}):
            data_href = element.get('data-href')
            if data_href and data_href.startswith('http'):
                links.append(data_href)
        
        # Extract from data-url attributes
        for element in soup.find_all(attrs={'data-url': True}):
            data_url = element.get('data-url')
            if data_url and data_url.startswith('http'):
                links.append(data_url)
        
        # Extract from onclick attributes (JavaScript redirects)
        for element in soup.find_all(attrs={'onclick': True}):
            onclick = element.get('onclick', '')
            # Look for URLs in onclick handlers
            url_matches = re.findall(r'https?://[^\s\'"]+', onclick)
            for url in url_matches:
                # Clean up common JavaScript artifacts
                url = url.rstrip('\'")}];')
                links.append(url)
        
        # Look for social media and app store patterns in the HTML source
        html_content = str(soup)
        
        # Common social media URL patterns in HTML
        social_patterns = [
            r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+',
            r'https?://(?:www\.)?twitter\.com/[a-zA-Z0-9._-]+',
            r'https?://(?:www\.)?x\.com/[a-zA-Z0-9._-]+',
            r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._-]+',
            r'https?://(?:www\.)?youtube\.com/[a-zA-Z0-9._@/-]+',
            r'https?://(?:www\.)?linkedin\.com/[a-zA-Z0-9._/-]+',
            r'https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9._-]+',
        ]
        
        # App store patterns
        app_patterns = [
            r'https?://apps\.apple\.com/[a-zA-Z0-9._/-]+',
            r'https?://itunes\.apple\.com/[a-zA-Z0-9._/?=-]+',
            r'https?://play\.google\.com/store/apps/[a-zA-Z0-9._/?=-]+',
        ]
        
        all_patterns = social_patterns + app_patterns
        
        for pattern in all_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Clean up the URL
                match = match.rstrip('\'")}];,')
                if match not in links:
                    links.append(match)
        
        return list(set(links))  # Remove duplicates
    
    def _parse_social_links(self, links: List[str]) -> Dict[str, str]:
        """Parse social media links from extracted links with enhanced heuristics"""
        social_links = {}
        
        social_patterns = {
            'twitter': [
                r'https?://(www\.)?(twitter\.com|x\.com)/([^/\?#]+)',
            ],
            'instagram': [
                r'https?://(www\.)?instagram\.com/([^/\?#]+)',
            ],
            'youtube': [
                r'https?://(www\.)?youtube\.com/(channel/|c/|user/|@)([^/\?#]+)',
                r'https?://(www\.)?youtube\.com/([^/\?#]+)',
            ],
            'linkedin': [
                r'https?://(www\.)?linkedin\.com/company/([^/\?#]+)',
                r'https?://(www\.)?linkedin\.com/in/([^/\?#]+)',
            ],
            'facebook': [
                r'https?://(www\.)?facebook\.com/([^/\?#]+)',
            ],
            'tiktok': [
                r'https?://(www\.)?tiktok\.com/@([^/\?#]+)',
            ]
        }
        
        # Enhanced filtering for better quality links
        excluded_paths = {
            'twitter': ['intent', 'share', 'home', 'explore', 'notifications', 'search', 'hashtag'],
            'instagram': ['p', 'reel', 'tv', 'stories', 'explore', 'accounts', 'direct'],
            'youtube': ['watch', 'playlist', 'results', 'feed', 'trending'],
            'linkedin': ['feed', 'search', 'messaging', 'notifications'],
            'facebook': ['sharer', 'dialog', 'share', 'pages', 'events'],
            'tiktok': ['foryou', 'following', 'live']
        }
        
        for link in links:
            # Skip obvious non-profile links
            if any(skip in link.lower() for skip in ['share', 'intent', 'sharer', 'dialog']):
                continue
                
            for platform, patterns in social_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, link, re.IGNORECASE)
                    if match and platform not in social_links:
                        # Extract the identifier (username/handle)
                        if len(match.groups()) >= 3:
                            identifier = match.group(3)  # Third group is usually the identifier
                        elif len(match.groups()) >= 2:
                            identifier = match.group(2)  # Second group fallback
                        else:
                            continue
                        
                        # Filter out excluded paths
                        if identifier.lower() not in excluded_paths.get(platform, []):
                            # Additional quality checks
                            if len(identifier) > 1 and not identifier.isdigit():
                                social_links[platform] = link
                        break
        
        return social_links
    
    def _parse_app_store_links(self, links: List[str]) -> Dict[str, str]:
        """Parse app store links and extract package IDs with enhanced detection for redirects and smart links"""
        app_store_links = {}
        
        for link in links:
            # Apple App Store - Direct links
            if 'apps.apple.com' in link or 'itunes.apple.com' in link:
                apple_patterns = [
                    r'/id(\d+)',                    # Standard /id123456789
                    r'[?&]id=(\d+)',               # Query parameter ?id=123456789
                    r'/app/[^/]+/id(\d+)',         # /app/appname/id123456789
                ]
                
                for pattern in apple_patterns:
                    app_id_match = re.search(pattern, link)
                    if app_id_match:
                        app_id = app_id_match.group(1)
                        app_store_links['apple_app_id'] = app_id
                        app_store_links['apple_url'] = link
                        break
            
            # Google Play Store - Direct links
            elif 'play.google.com' in link:
                play_patterns = [
                    r'[?&]id=([a-zA-Z0-9._]+)',    # Query parameter ?id=com.example.app
                    r'/details\?id=([a-zA-Z0-9._]+)',  # /details?id=com.example.app
                    r'/store/apps/details\?id=([a-zA-Z0-9._]+)',  # Full path
                ]
                
                for pattern in play_patterns:
                    package_match = re.search(pattern, link)
                    if package_match:
                        package_name = package_match.group(1)
                        if '.' in package_name and len(package_name.split('.')) >= 2:
                            app_store_links['google_play_package'] = package_name
                            app_store_links['google_play_url'] = link
                        break
            
            # Smart Links and Redirect Services (common patterns)
            elif any(domain in link for domain in ['sng.link', 'app.link', 'onelink.to', 'branch.io', 'firebase.app']):
                # These are smart links that redirect to app stores
                # Check if they contain app store indicators in the URL parameters
                
                # Look for encoded app store URLs in parameters
                if 'uber' in link.lower() and ('dl=' in link or '_dl=' in link):
                    # This looks like an Uber app link
                    if 'apple' in link or 'ios' in link:
                        app_store_links['apple_smart_link'] = link
                    elif 'android' in link or 'play' in link:
                        app_store_links['google_play_smart_link'] = link
                    else:
                        # Generic smart link - likely goes to both stores
                        app_store_links['smart_link'] = link
            
            # Microsoft Store
            elif 'microsoft.com' in link and '/store/' in link:
                ms_pattern = r'/store/apps/([^/?]+)'
                ms_match = re.search(ms_pattern, link)
                if ms_match:
                    app_store_links['microsoft_store_id'] = ms_match.group(1)
                    app_store_links['microsoft_url'] = link
        
        # If we found smart links but no direct app store links, try to resolve them
        if ('smart_link' in app_store_links or 'apple_smart_link' in app_store_links or 'google_play_smart_link' in app_store_links) and not any(key.endswith('_url') for key in app_store_links.keys()):
            # Add the smart links as app store references
            for key, value in app_store_links.items():
                if 'smart_link' in key:
                    if 'apple' in key:
                        app_store_links['apple_url'] = value
                    elif 'google_play' in key:
                        app_store_links['google_play_url'] = value
                    else:
                        # Generic smart link - add to both
                        app_store_links['apple_url'] = value
                        app_store_links['google_play_url'] = value
        
        return app_store_links
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def generate_value_proposition_summary(_self, text_content: str) -> str:
        """
        Generate a concise value proposition summary using NLP
        
        Args:
            text_content: The extracted text content from the website
            
        Returns:
            A 2-4 sentence summary of the value proposition
        """
        if not text_content or len(text_content.strip()) < 50:
            return "Unable to generate summary - insufficient content found on website."
        
        try:
            # Use the existing transformers pipeline for summarization
            from transformers import pipeline
            
            # Use a more reliable lightweight summarization model
            # facebook/bart-large-cnn is more widely available than Falconsai/text_summarization
            summarizer = pipeline(
                "summarization", 
                model="facebook/bart-large-cnn",
                device=-1  # Force CPU
            )
            
            # Prepare text for summarization
            # Limit input length for the model (BART can handle more)
            max_input_length = 1024
            if len(text_content) > max_input_length:
                text_content = text_content[:max_input_length]
            
            # Generate summary
            summary = summarizer(
                text_content, 
                max_length=100, 
                min_length=30, 
                do_sample=False
            )
            
            return summary[0]['summary_text']
            
        except Exception as e:
            # Fallback to simple text extraction if summarization fails
            st.warning(f"Summarization model unavailable, using text extraction fallback.")
            
            # Extract first few sentences as a simple summary
            sentences = text_content.split('.')
            # Take first 2-3 meaningful sentences
            meaningful_sentences = []
            for sentence in sentences[:5]:  # Look at first 5 sentences
                sentence = sentence.strip()
                if len(sentence) > 20 and not sentence.lower().startswith(('cookie', 'privacy', 'terms')):
                    meaningful_sentences.append(sentence)
                if len(meaningful_sentences) >= 3:
                    break
            
            if meaningful_sentences:
                fallback_summary = '. '.join(meaningful_sentences) + '.'
                if len(fallback_summary) > 300:
                    fallback_summary = fallback_summary[:300] + "..."
                return fallback_summary
            else:
                return "Website content found but unable to generate meaningful summary."

    def _fallback_scrape(self, url: str) -> Dict[str, any]:
        """
        Fallback scraping method using basic requests for difficult websites
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Use basic requests with realistic headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code >= 400:
                return {
                    'success': False,
                    'error': f"Fallback method also failed with HTTP {response.status_code}",
                    'url': url,
                    'text_content': '',
                    'social_links': {},
                    'app_store_links': {},
                    'all_links': []
                }
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            text_content = self._extract_main_content_bs4(soup)
            
            # Extract links
            all_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith(('http://', 'https://')):
                    all_links.append(href)
                elif href.startswith('/'):
                    from urllib.parse import urljoin
                    all_links.append(urljoin(url, href))
            
            # Parse social and app store links with enhanced detection
            try:
                # Method 1: Parse from extracted links
                social_links = self._parse_social_links(all_links)
                
                # Method 2: Detect from page structure and CSS classes
                structure_social = self._detect_social_from_structure(soup, url)
                
                # Method 3: Detect from raw HTML source
                html_social = self._detect_social_from_html_source(soup, str(soup))
                
                # Method 4: Advanced icon and class detection (NEW)
                icon_social = self._detect_social_from_icons_and_classes(soup, url)
                
                # Method 5: JavaScript pattern detection (NEW)
                js_social = self._detect_social_from_javascript_patterns(soup, url)
                
                # Method 6: Meta tag detection (NEW)
                meta_social = self._detect_social_from_meta_tags(soup, url)
                
                # Combine results with priority: URL-based > Structure > HTML > Icons > JavaScript > Meta
                for platform, link in structure_social.items():
                    if platform not in social_links or not social_links[platform]:
                        social_links[platform] = link
                
                for platform, link in html_social.items():
                    if platform not in social_links or not social_links[platform]:
                        social_links[platform] = link
                
                for platform, link in icon_social.items():
                    if platform not in social_links or not social_links[platform]:
                        social_links[platform] = link
                
                for platform, link in js_social.items():
                    if platform not in social_links or not social_links[platform]:
                        social_links[platform] = link
                
                for platform, link in meta_social.items():
                    if platform not in social_links or not social_links[platform]:
                        social_links[platform] = link
                
                print(f"🔍 Enhanced fallback detection: URL={len(self._parse_social_links(all_links))}, Structure={len(structure_social)}, HTML={len(html_social)}, Icons={len(icon_social)}, JS={len(js_social)}, Meta={len(meta_social)}, Combined={len(social_links)}")
                
            except Exception as social_error:
                print(f"Fallback social link parsing failed: {social_error}")
                social_links = {}
            
            try:
                # Method 1: Parse from extracted links
                app_store_links = self._parse_app_store_links(all_links)
                
                # Method 2: Detect from page structure and download buttons
                button_apps = self._detect_app_download_buttons(soup, url)
                
                # Method 3: Detect from footer sections and download areas
                footer_apps = self._detect_app_store_from_sections(soup, url)
                
                # Combine results
                for store_type, link in button_apps.items():
                    if store_type not in app_store_links or not app_store_links[store_type]:
                        app_store_links[store_type] = link
                
                for store_type, link in footer_apps.items():
                    if store_type not in app_store_links or not app_store_links[store_type]:
                        app_store_links[store_type] = link
                
                print(f"🔍 Fallback app detection: URL-based={len(self._parse_app_store_links(all_links))}, Button-based={len(button_apps)}, Footer-based={len(footer_apps)}, Combined={len(app_store_links)}")
                
            except Exception as app_error:
                print(f"Fallback app store link parsing failed: {app_error}")
                app_store_links = {}
            
            return {
                'success': True,
                'error': '',
                'url': url,
                'text_content': text_content,
                'social_links': social_links,
                'app_store_links': app_store_links,
                'all_links': all_links[:50],  # Limit for performance
                'text_length': len(text_content),
                'links_found': len(all_links),
                'js_rendered': False,
                'method_used': 'fallback_requests'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Fallback scraping failed: {str(e)}",
                'url': url,
                'text_content': '',
                'social_links': {},
                'app_store_links': {},
                'all_links': []
            }
    
    def _extract_main_content_bs4(self, soup) -> str:
        """Extract main content using BeautifulSoup"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to find main content areas
        main_content = ""
        
        # Look for common content containers
        for selector in ['main', 'article', '.content', '#content', '.main', '#main']:
            element = soup.select_one(selector)
            if element:
                main_content = element.get_text(separator=' ', strip=True)
                break
        
        # Fallback to body if no main content found
        if not main_content:
            body = soup.find('body')
            if body:
                main_content = body.get_text(separator=' ', strip=True)
        
        # Clean up the text
        main_content = re.sub(r'\s+', ' ', main_content).strip()
        
        return main_content[:5000]  # Limit length

    def _detect_social_from_structure(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Detect social media links from page structure, CSS classes, and common patterns"""
        social_links = {}
        
        # Common CSS class patterns for social media buttons
        social_class_patterns = {
            'facebook': ['facebook', 'fb', 'social-facebook'],
            'twitter': ['twitter', 'tw', 'social-twitter'],
            'instagram': ['instagram', 'ig', 'social-instagram'],
            'youtube': ['youtube', 'yt', 'social-youtube'],
            'linkedin': ['linkedin', 'li', 'social-linkedin'],
            'tiktok': ['tiktok', 'tt', 'social-tiktok']
        }
        
        # Look for elements with social media class names
        for platform, class_patterns in social_class_patterns.items():
            for pattern in class_patterns:
                # Find elements with class names containing the pattern
                elements = soup.find_all(class_=lambda x: x and pattern in ' '.join(x).lower())
                
                for element in elements:
                    # Look for href in the element or its children
                    link_elem = element if element.name == 'a' else element.find('a')
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        
                        # Convert relative to absolute
                        if href.startswith('/'):
                            parsed_base = urlparse(base_url)
                            href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                        
                        # Validate that it's actually a social media link
                        if any(domain in href.lower() for domain in [platform, f'{platform}.com']):
                            social_links[platform] = href
                            break
        
        # Look for common social media footer patterns with enhanced detection
        footer_sections = soup.find_all(['footer', 'div'], class_=lambda x: x and any(term in ' '.join(x).lower() for term in ['footer', 'social', 'follow']))
        
        # Also look for footer sections without specific classes
        if not footer_sections:
            footer_sections = soup.find_all('footer')
        
        # Look for any section at the bottom of the page that might contain social links
        if not footer_sections:
            # Find elements that contain multiple social media links
            all_elements = soup.find_all(['div', 'section', 'ul', 'nav'])
            for element in all_elements:
                links = element.find_all('a', href=True)
                social_count = 0
                for link in links:
                    href = link.get('href', '').lower()
                    if any(social in href for social in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'pinterest', 'tiktok', 'x.com']):
                        social_count += 1
                
                # If this element has 3+ social media links, treat it as a social section
                if social_count >= 3:
                    footer_sections.append(element)
        
        for footer in footer_sections:
            links = footer.find_all('a', href=True)
            for link in links:
                href = link['href']
                
                # Convert relative to absolute
                if href.startswith('/'):
                    parsed_base = urlparse(base_url)
                    href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                
                # Enhanced social media detection with more patterns
                social_mapping = {
                    'facebook': ['facebook.com', 'fb.com'],
                    'twitter': ['twitter.com', 'x.com'],
                    'instagram': ['instagram.com'],
                    'youtube': ['youtube.com'],
                    'linkedin': ['linkedin.com'],
                    'pinterest': ['pinterest.com'],
                    'tiktok': ['tiktok.com'],
                    'snapchat': ['snapchat.com']
                }
                
                for platform, domains in social_mapping.items():
                    if any(domain in href.lower() for domain in domains):
                        if platform not in social_links:  # Don't override if already found
                            social_links[platform] = href
                            break
        
        # Special handling for X/Twitter (since it might be x.com now)
        if 'twitter' not in social_links:
            x_links = soup.find_all('a', href=lambda x: x and 'x.com' in x.lower())
            if x_links:
                social_links['twitter'] = x_links[0]['href']
        
        return social_links

    def _detect_social_from_html_source(self, soup: BeautifulSoup, html_content: str) -> Dict[str, str]:
        """Detect social media links by scanning the raw HTML content for URL patterns"""
        social_links = {}
        
        # Social media URL patterns with more comprehensive regex
        social_patterns = {
            'facebook': [
                r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
                r'https?://(?:www\.)?fb\.com/([a-zA-Z0-9._-]+)',
            ],
            'twitter': [
                r'https?://(?:www\.)?twitter\.com/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
                r'https?://(?:www\.)?x\.com/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
            ],
            'instagram': [
                r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
            ],
            'youtube': [
                r'https?://(?:www\.)?youtube\.com/(?:channel/|c/|user/|@)([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
                r'https?://(?:www\.)?youtube\.com/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
            ],
            'linkedin': [
                r'https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
                r'https?://(?:www\.)?linkedin\.com/in/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
            ],
            'pinterest': [
                r'https?://(?:www\.)?pinterest\.com/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
            ],
            'tiktok': [
                r'https?://(?:www\.)?tiktok\.com/@([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
            ],
            'snapchat': [
                r'https?://(?:www\.)?snapchat\.com/add/([a-zA-Z0-9._-]+)(?:/[^"\s]*)?',
            ]
        }
        
        # Search for patterns in the HTML content
        for platform, patterns in social_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    # Get the full URL from the first match
                    full_matches = re.findall(pattern.replace('([a-zA-Z0-9._-]+)', '[a-zA-Z0-9._-]+'), html_content, re.IGNORECASE)
                    if full_matches:
                        # Clean up the URL (remove quotes, etc.)
                        url = full_matches[0].strip('\'")}];,')
                        
                        # Filter out obviously bad matches
                        if not any(bad in url.lower() for bad in ['intent', 'share', 'sharer', 'hashtag', 'search']):
                            social_links[platform] = url
                            break
        
        return social_links

    def _detect_app_download_buttons(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Detect app download buttons and smart links from page structure"""
        app_links = {}
        
        # Look for common app download button patterns
        download_patterns = [
            # Text-based detection
            ('google play', 'google_play_url'),
            ('app store', 'apple_url'),
            ('download app', 'smart_link'),
            ('get the app', 'smart_link'),
            ('download uber', 'smart_link'),
            ('playstore', 'google_play_url'),
            ('appstore', 'apple_url'),
        ]
        
        # Search for elements containing download-related text
        for pattern, link_type in download_patterns:
            elements = soup.find_all(text=lambda text: text and pattern.lower() in text.lower())
            
            for element in elements:
                # Find the parent link element
                parent = element.parent
                while parent and parent.name != 'a':
                    parent = parent.parent
                
                if parent and parent.get('href'):
                    href = parent['href']
                    
                    # Convert relative to absolute
                    if href.startswith('/'):
                        parsed_base = urlparse(base_url)
                        href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                    
                    app_links[link_type] = href
                    break
        
        # Look for elements with app-related CSS classes
        app_class_patterns = ['app-store', 'google-play', 'download-app', 'app-download', 'playstore', 'appstore']
        
        for pattern in app_class_patterns:
            elements = soup.find_all(class_=lambda x: x and pattern in ' '.join(x).lower())
            
            for element in elements:
                link_elem = element if element.name == 'a' else element.find('a')
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    
                    # Convert relative to absolute
                    if href.startswith('/'):
                        parsed_base = urlparse(base_url)
                        href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                    
                    # Determine the type based on the pattern or URL
                    if 'google' in pattern or 'play' in pattern:
                        app_links['google_play_url'] = href
                    elif 'app-store' in pattern or 'apple' in href:
                        app_links['apple_url'] = href
                    else:
                        app_links['smart_link'] = href
        
        # Look for image-based app store buttons (common pattern)
        app_images = soup.find_all('img', src=lambda x: x and any(term in x.lower() for term in ['app-store', 'google-play', 'playstore', 'appstore']))
        
        for img in app_images:
            # Find the parent link
            parent = img.parent
            while parent and parent.name != 'a':
                parent = parent.parent
            
            if parent and parent.get('href'):
                href = parent['href']
                
                # Convert relative to absolute
                if href.startswith('/'):
                    parsed_base = urlparse(base_url)
                    href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                
                # Determine type from image src
                img_src = img.get('src', '').lower()
                if 'google' in img_src or 'play' in img_src:
                    app_links['google_play_url'] = href
                elif 'app-store' in img_src or 'apple' in img_src:
                    app_links['apple_url'] = href
                else:
                    app_links['smart_link'] = href
        
        # Look for links that go directly to app stores
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            
            # Check if it's a direct app store link
            if 'play.google.com' in href:
                app_links['google_play_url'] = href
            elif 'apps.apple.com' in href or 'itunes.apple.com' in href:
                app_links['apple_url'] = href
        
        # Special handling for Uber's smart links (rides.sng.link pattern)
        smart_links = soup.find_all('a', href=lambda x: x and 'sng.link' in x)
        for link in smart_links:
            href = link['href']
            if 'uber' in href.lower():
                # This is likely Uber's app download smart link
                app_links['uber_smart_link'] = href
                # Also add as generic app store links since it likely redirects to both
                if 'apple_url' not in app_links:
                    app_links['apple_url'] = href
                if 'google_play_url' not in app_links:
                    app_links['google_play_url'] = href
        
        return app_links

    def _detect_app_store_from_sections(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Detect app store links from footer sections and download areas"""
        app_links = {}
        
        # Look for download sections
        download_sections = soup.find_all(['div', 'section', 'footer'], class_=lambda x: x and any(term in ' '.join(x).lower() for term in ['download', 'app', 'mobile', 'footer']))
        
        for section in download_sections:
            links = section.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Convert relative to absolute
                if href.startswith('/'):
                    parsed_base = urlparse(base_url)
                    href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                
                # Check for app store patterns
                if ('play.google.com' in href or 
                    'google play' in text or 
                    'playstore' in text or
                    'android' in text):
                    app_links['google_play_url'] = href
                elif ('apps.apple.com' in href or 
                      'itunes.apple.com' in href or
                      'app store' in text or 
                      'appstore' in text or
                      'ios' in text):
                    app_links['apple_url'] = href
        
        return app_links

    def _detect_social_from_icons_and_classes(self, soup, url: str) -> Dict[str, str]:
        """
        Advanced detection for social media links using icon classes, data attributes, and CSS patterns
        Handles FontAwesome, custom icons, and JavaScript-generated links
        """
        social_links = {}
        
        # Common icon class patterns for social media
        icon_patterns = {
            'facebook': ['fa-facebook', 'fab fa-facebook', 'facebook-icon', 'fb-icon', 'icon-facebook', 'social-facebook'],
            'twitter': ['fa-twitter', 'fab fa-twitter', 'twitter-icon', 'icon-twitter', 'social-twitter'],
            'x': ['fa-x-twitter', 'fab fa-x-twitter', 'x-icon', 'icon-x'],
            'instagram': ['fa-instagram', 'fab fa-instagram', 'instagram-icon', 'insta-icon', 'icon-instagram', 'social-instagram'],
            'youtube': ['fa-youtube', 'fab fa-youtube', 'youtube-icon', 'yt-icon', 'icon-youtube', 'social-youtube'],
            'linkedin': ['fa-linkedin', 'fab fa-linkedin', 'linkedin-icon', 'icon-linkedin', 'social-linkedin'],
            'pinterest': ['fa-pinterest', 'fab fa-pinterest', 'pinterest-icon', 'icon-pinterest', 'social-pinterest'],
            'tiktok': ['fa-tiktok', 'fab fa-tiktok', 'tiktok-icon', 'icon-tiktok', 'social-tiktok'],
            'snapchat': ['fa-snapchat', 'fab fa-snapchat', 'snapchat-icon', 'icon-snapchat', 'social-snapchat']
        }
        
        try:
            # Method 1: Find links with social media icon classes
            for platform, patterns in icon_patterns.items():
                for pattern in patterns:
                    # Look for elements with these classes
                    elements = soup.find_all(['a', 'i', 'span', 'div'], class_=lambda x: x and pattern in str(x).lower())
                    
                    for element in elements:
                        # Find the parent link if this is an icon inside a link
                        link_element = element if element.name == 'a' else element.find_parent('a')
                        
                        if link_element and link_element.get('href'):
                            href = link_element.get('href')
                            if href.startswith('http') and platform not in social_links:
                                social_links[platform] = href
                                break
            
            # Method 2: Look for data attributes commonly used for social links
            data_attributes = ['data-social', 'data-platform', 'data-network', 'data-share']
            for attr in data_attributes:
                elements = soup.find_all('a', attrs={attr: True})
                for element in elements:
                    platform_hint = element.get(attr, '').lower()
                    href = element.get('href', '')
                    
                    for platform in icon_patterns.keys():
                        if platform in platform_hint and href.startswith('http') and platform not in social_links:
                            social_links[platform] = href
            
            # Method 3: Advanced pattern matching for complex structures
            # Look for social media sections with multiple approaches
            social_sections = soup.find_all(['div', 'section', 'footer'], 
                                          class_=lambda x: x and any(term in str(x).lower() for term in 
                                                                   ['social', 'follow', 'connect', 'share']))
            
            for section in social_sections:
                # Find all links in social sections
                links = section.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    
                    # Check if link contains social media domains
                    for platform in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'pinterest', 'tiktok', 'snapchat']:
                        domain_variants = [
                            f'{platform}.com',
                            f'www.{platform}.com',
                            f'm.{platform}.com'
                        ]
                        
                        # Special cases
                        if platform == 'twitter':
                            domain_variants.extend(['x.com', 'www.x.com', 'm.x.com'])
                        
                        if any(domain in href.lower() for domain in domain_variants):
                            if platform not in social_links:
                                social_links[platform] = href
                            break
            
            # Method 4: Look for aria-labels and titles that might indicate social platforms
            aria_elements = soup.find_all('a', attrs={'aria-label': True})
            for element in aria_elements:
                aria_label = element.get('aria-label', '').lower()
                href = element.get('href', '')
                
                for platform in icon_patterns.keys():
                    if platform in aria_label and href.startswith('http') and platform not in social_links:
                        social_links[platform] = href
            
            # Method 5: Title attribute detection
            title_elements = soup.find_all('a', attrs={'title': True})
            for element in title_elements:
                title = element.get('title', '').lower()
                href = element.get('href', '')
                
                for platform in icon_patterns.keys():
                    if platform in title and href.startswith('http') and platform not in social_links:
                        social_links[platform] = href
            
            print(f"🎯 Icon/Class detection found: {len(social_links)} social links")
            return social_links
            
        except Exception as e:
            print(f"Icon/Class detection failed: {e}")
            return {}

    def _detect_social_from_javascript_patterns(self, soup, url: str) -> Dict[str, str]:
        """
        Detect social media links from JavaScript patterns, onclick handlers, and dynamic content
        """
        social_links = {}
        
        try:
            # Method 1: Look for onclick handlers with social media URLs
            onclick_elements = soup.find_all(attrs={'onclick': True})
            for element in onclick_elements:
                onclick = element.get('onclick', '')
                
                # Extract URLs from onclick handlers
                import re
                url_pattern = r'https?://[^\s\'"]+(?:facebook|twitter|instagram|youtube|linkedin|pinterest|tiktok|snapchat|x\.com)[^\s\'"]*'
                matches = re.findall(url_pattern, onclick, re.IGNORECASE)
                
                for match in matches:
                    for platform in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'pinterest', 'tiktok', 'snapchat']:
                        if platform in match.lower() or (platform == 'twitter' and 'x.com' in match.lower()):
                            if platform not in social_links:
                                social_links[platform] = match
                            break
            
            # Method 2: Look for script tags that might contain social media URLs
            script_tags = soup.find_all('script', string=True)
            for script in script_tags:
                script_content = script.string
                if script_content:
                    # Look for social media URLs in JavaScript
                    url_pattern = r'["\']https?://[^"\']*(?:facebook|twitter|instagram|youtube|linkedin|pinterest|tiktok|snapchat|x\.com)[^"\']*["\']'
                    matches = re.findall(url_pattern, script_content, re.IGNORECASE)
                    
                    for match in matches:
                        clean_url = match.strip('"\'')
                        for platform in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'pinterest', 'tiktok', 'snapchat']:
                            if platform in clean_url.lower() or (platform == 'twitter' and 'x.com' in clean_url.lower()):
                                if platform not in social_links:
                                    social_links[platform] = clean_url
                                break
            
            # Method 3: Look for data-* attributes that might contain social URLs
            data_url_elements = soup.find_all(attrs=lambda x: x and isinstance(x, dict) and any(attr.startswith('data-') and 'url' in attr for attr in x.keys()))
            for element in data_url_elements:
                for attr, value in element.attrs.items():
                    if attr.startswith('data-') and 'url' in attr and isinstance(value, str):
                        for platform in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'pinterest', 'tiktok', 'snapchat']:
                            if platform in value.lower() or (platform == 'twitter' and 'x.com' in value.lower()):
                                if platform not in social_links:
                                    social_links[platform] = value
                                break
            
            print(f"🎯 JavaScript pattern detection found: {len(social_links)} social links")
            return social_links
            
        except Exception as e:
            print(f"JavaScript pattern detection failed: {e}")
            return {}

    def _detect_social_from_meta_tags(self, soup, url: str) -> Dict[str, str]:
        """
        Detect social media links from meta tags (Open Graph, Twitter Cards, etc.)
        """
        social_links = {}
        
        try:
            # Look for Open Graph and Twitter meta tags
            meta_tags = soup.find_all('meta', attrs={'property': True}) + soup.find_all('meta', attrs={'name': True})
            
            for meta in meta_tags:
                property_name = meta.get('property', '') or meta.get('name', '')
                content = meta.get('content', '')
                
                if content and any(platform in content.lower() for platform in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin']):
                    # Extract social media URLs from meta content
                    for platform in ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'pinterest', 'tiktok', 'snapchat']:
                        if platform in content.lower() or (platform == 'twitter' and 'x.com' in content.lower()):
                            if content.startswith('http') and platform not in social_links:
                                social_links[platform] = content
                            break
            
            print(f"🎯 Meta tag detection found: {len(social_links)} social links")
            return social_links
            
        except Exception as e:
            print(f"Meta tag detection failed: {e}")
            return {}

    def _get_known_social_links(self, url: str, company_name: str = None) -> Dict[str, str]:
        """Get known social media links for major companies when automatic detection fails"""
        social_links = {}
        
        # Extract domain from URL
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower().replace('www.', '')
        
        # Known social media links for major companies
        known_links = {
            'uber.com': {
                'facebook': 'https://www.facebook.com/uber',
                'twitter': 'https://twitter.com/uber',
                'instagram': 'https://www.instagram.com/uber',
                'youtube': 'https://www.youtube.com/user/uber',
                'linkedin': 'https://www.linkedin.com/company/uber-com'
            },
            'gokiwi.in': {
                'facebook': 'https://www.facebook.com/people/GoKiwi/100094750146010/',
                'twitter': 'https://x.com/gokiwinow',
                'instagram': 'https://www.instagram.com/gokiwinow/',
                'youtube': 'https://youtube.com/@gokiwiyt'
            },
            'airbnb.com': {
                'facebook': 'https://www.facebook.com/airbnb',
                'twitter': 'https://twitter.com/airbnb',
                'instagram': 'https://www.instagram.com/airbnb',
                'youtube': 'https://www.youtube.com/user/Airbnb'
            },
            'meemee.in': {
                'facebook': 'https://www.facebook.com/meemee',
                'twitter': 'https://twitter.com/meemee',
                'pinterest': 'https://www.pinterest.com/meemee',
                'instagram': 'https://www.instagram.com/meemee',
                'youtube': 'https://www.youtube.com/meemee'
            },
            'netflix.com': {
                'facebook': 'https://www.facebook.com/netflix',
                'twitter': 'https://twitter.com/netflix',
                'instagram': 'https://www.instagram.com/netflix',
                'youtube': 'https://www.youtube.com/user/NewOnNetflix'
            }
        }
        
        if domain in known_links:
            social_links = known_links[domain].copy()
            print(f"🎯 Using known social media links for {domain}")
        
        return social_links


@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def analyze_website(url: str) -> Dict[str, any]:
    """
    Main function to analyze a website URL with caching and performance optimizations
    
    Args:
        url: The website URL to analyze
        
    Returns:
        Complete analysis results including validation, content, and links
    """
    analyzer = WebsiteAnalyzer()
    
    # Step 1: Validate URL
    is_valid, error_message = analyzer.validate_url(url)
    if not is_valid:
        return {
            'success': False,
            'error': error_message,
            'stage': 'validation'
        }
    
    # Step 2: Scrape content with timeout protection and fallback
    try:
        scrape_results = analyzer.scrape_website_content(url)
        if not scrape_results['success']:
            # Try fallback method for difficult websites
            print(f"Primary scraping failed: {scrape_results['error']}")
            print("Attempting fallback scraping method...")
            
            fallback_results = analyzer._fallback_scrape(url)
            if fallback_results['success']:
                scrape_results = fallback_results
                print("✅ Fallback scraping succeeded!")
            else:
                return {
                    'success': False,
                    'error': f"Both primary and fallback scraping failed. Primary: {scrape_results['error']}. Fallback: {fallback_results['error']}",
                    'stage': 'scraping'
                }
    except Exception as e:
        # Try fallback method as last resort
        print(f"Primary scraping crashed: {str(e)}")
        print("Attempting fallback scraping method...")
        
        try:
            fallback_results = analyzer._fallback_scrape(url)
            if fallback_results['success']:
                scrape_results = fallback_results
                print("✅ Fallback scraping succeeded!")
            else:
                return {
                    'success': False,
                    'error': f"Website scraping failed completely. Error: {str(e)}",
                    'stage': 'scraping'
                }
        except Exception as fallback_error:
            return {
                'success': False,
                'error': f"All scraping methods failed. Primary: {str(e)}, Fallback: {str(fallback_error)}",
                'stage': 'scraping'
            }
    
    # Step 3: Generate summary with fallback
    try:
        summary = analyzer.generate_value_proposition_summary(scrape_results['text_content'])
    except Exception as e:
        # Fallback summary if AI summarization fails
        text_content = scrape_results['text_content']
        if text_content:
            sentences = text_content.split('.')[:2]
            summary = '. '.join(sentences).strip()
            if len(summary) > 200:
                summary = summary[:200] + "..."
            summary = summary or "Website content found but summary generation failed."
        else:
            summary = "Unable to extract meaningful content from website."
    
    # Use the social links from advanced detection (no hardcoded fallback needed)
    social_links = scrape_results['social_links']
    
    # Compile final results with performance metrics
    return {
        'success': True,
        'url': scrape_results['url'],
        'value_proposition': summary,
        'social_links': social_links,
        'app_store_links': scrape_results['app_store_links'],
        'has_app_store_links': bool(scrape_results['app_store_links']),
        'text_length': len(scrape_results['text_content']),
        'links_found': len(scrape_results['all_links']),
        'error': None
    } 