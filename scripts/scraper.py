# scripts/scraper.py - FIXED HIERARCHICAL SCRAPER

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
import time
import json
from pathlib import Path
import sys
import re
from urllib.parse import urljoin, urlparse, urldefrag

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.config import SCRAPED_DIR, MODULES_DIR


class JainWorldHierarchicalScraper:
    """
    Fixed hierarchical scraper for Jainworld.com
    Properly handles URL fragments and parent-child relationships
    """
    
    def __init__(self, max_depth: int = 3, max_pages: int = 100):
        self.base_url = "https://jainworld.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.visited_urls: Set[str] = set()
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.scraped_documents = []
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments and trailing slashes
        
        Args:
            url: Raw URL
            
        Returns:
            Normalized URL without fragments
        """
        # Remove fragment (#content, #footer, etc.)
        url, _ = urldefrag(url)
        
        # Remove trailing slash for consistency
        url = url.rstrip('/')
        
        return url
    
    def is_direct_child(self, parent_url: str, child_url: str) -> bool:
        """
        Check if child_url is a direct child of parent_url
        (not a sibling or grandchild)
        
        Args:
            parent_url: Parent URL
            child_url: Potential child URL
            
        Returns:
            True if direct child, False otherwise
        """
        parent_path = urlparse(parent_url).path.rstrip('/')
        child_path = urlparse(child_url).path.rstrip('/')
        
        # Child path must start with parent path
        if not child_path.startswith(parent_path):
            return False
        
        # Get the relative part
        relative = child_path[len(parent_path):].strip('/')
        
        # Direct child has exactly one more path segment
        # e.g., /philosophy/ -> /philosophy/ahimsa/ (direct child)
        # but  /philosophy/ -> /philosophy/ahimsa/introduction/ (grandchild)
        
        if not relative:
            return False  # Same URL
        
        # Count slashes in relative part
        slash_count = relative.count('/')
        
        # Direct child has 0 slashes (e.g., "ahimsa-non-violence")
        return slash_count == 0
    
    def fetch_page(self, url: str, delay: float = 2.0) -> Optional[str]:
        """Fetch a single page with rate limiting"""
        try:
            time.sleep(delay)
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:50]}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.\,\!\?\-\(\)\:\;\'\"\n]', '', text)
        return text.strip()
    
    def extract_direct_child_links(self, html: str, parent_url: str) -> List[str]:
        """
        Extract only DIRECT child links from a page
        
        Args:
            html: Page HTML
            parent_url: URL of current page
            
        Returns:
            List of direct child URLs only
        """
        soup = BeautifulSoup(html, 'lxml')
        child_links = []
        
        # Find main content area to avoid header/footer links
        main_content = (soup.find('article') or 
                       soup.find('main') or
                       soup.find('div', class_=re.compile('content|entry|post', re.I)) or
                       soup.find('body'))
        
        if not main_content:
            return []
        
        # Look for links in the main content
        for a_tag in main_content.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip empty, javascript, mailto, tel links
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Make absolute URL
            if href.startswith('/'):
                full_url = self.base_url + href
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(parent_url, href)
            
            # Normalize (remove fragments)
            full_url = self.normalize_url(full_url)
            
            # Must be on jainworld.com
            if 'jainworld.com' not in full_url:
                continue
            
            # Skip file downloads
            if full_url.endswith(('.pdf', '.jpg', '.png', '.gif', '.zip', '.doc')):
                continue
            
            # Check if it's a direct child
            if self.is_direct_child(parent_url, full_url):
                if full_url not in child_links and full_url not in self.visited_urls:
                    child_links.append(full_url)
        
        return child_links
    
    def extract_content_from_page(self, html: str, url: str) -> Optional[Dict]:
        """Extract clean content from a page"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                            'aside', 'form', 'iframe', 'noscript', 'button']):
            element.decompose()
        
        # Get title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "Untitled"
        title_text = re.sub(r'\s*[-|]\s*Jainworld.*', '', title_text).strip()
        
        # Also try h1
        h1 = soup.find('h1')
        if h1:
            h1_text = h1.get_text().strip()
            if h1_text and len(h1_text) < 100:
                title_text = h1_text
        
        # Find main content
        main_content = (soup.find('article') or 
                       soup.find('main') or
                       soup.find('div', class_=re.compile('content|post|entry|article', re.I)) or
                       soup.find('div', id=re.compile('content|main|post', re.I)))
        
        if not main_content:
            # Try to find the div with most text
            all_divs = soup.find_all('div')
            max_text_length = 0
            for div in all_divs:
                text_length = len(div.get_text())
                if text_length > max_text_length:
                    max_text_length = text_length
                    main_content = div
        
        if not main_content:
            return None
        
        # Extract structured content
        content_parts = []
        for element in main_content.find_all(['h2', 'h3', 'h4', 'p', 'li', 'blockquote']):
            text = element.get_text().strip()
            
            # Filter out short snippets and navigation text
            if (len(text) > 20 and 
                not any(skip in text.lower() for skip in 
                       ['home', 'menu', 'search', 'contact', 'copyright', 'cookie', 
                        'privacy policy', 'terms of use', 'all rights reserved'])):
                content_parts.append(text)
        
        content = '\n\n'.join(content_parts)
        content = self.clean_text(content)
        
        # Must have substantial content
        if len(content) < 200:
            return None
        
        return {
            "title": title_text,
            "content": content,
            "word_count": len(content.split()),
            "source_url": url
        }
    
    def scrape_hierarchical(
        self, 
        start_url: str, 
        depth: int = 0,
        parent_category: str = "general"
    ) -> List[Dict]:
        """
        Recursively scrape a URL and its direct children
        
        Args:
            start_url: URL to start scraping from
            depth: Current depth (0 = root)
            parent_category: Category from parent
            
        Returns:
            List of scraped documents
        """
        # Normalize URL
        start_url = self.normalize_url(start_url)
        
        # Check limits
        if depth > self.max_depth:
            return []
        
        if len(self.visited_urls) >= self.max_pages:
            print(f"\n  ⚠️  Reached max pages limit ({self.max_pages})")
            return []
        
        if start_url in self.visited_urls:
            return []
        
        # Mark as visited
        self.visited_urls.add(start_url)
        
        # Fetch the page
        indent = "  " * depth
        print(f"\n{indent}{'📂' if depth == 0 else '📄'} [{depth}] {start_url.split('/')[-1] or 'index'}")
        print(f"{indent}    🌐 Fetching...")
        
        html = self.fetch_page(start_url)
        if not html:
            return []
        
        documents = []
        
        # Extract content from current page
        extracted = self.extract_content_from_page(html, start_url)
        
        if extracted:
            # Determine metadata
            category = self._categorize_content(start_url, extracted['content'])
            difficulty = self._determine_difficulty(extracted['content'])
            topic = self._extract_topic(extracted['title'], extracted['content'])
            
            doc = {
                "content": extracted['content'],
                "metadata": {
                    "source_url": start_url,
                    "title": extracted['title'],
                    "category": category,
                    "difficulty": difficulty,
                    "topic": topic,
                    "word_count": extracted['word_count'],
                    "depth": depth,
                    "scrape_date": time.strftime("%Y-%m-%d")
                }
            }
            
            documents.append(doc)
            print(f"{indent}    ✅ {extracted['title'][:50]}")
            print(f"{indent}    📊 {extracted['word_count']} words | {category} | {difficulty}")
        else:
            print(f"{indent}    ⚠️  No substantial content")
        
        # Find DIRECT child links only
        child_links = self.extract_direct_child_links(html, start_url)
        
        if child_links:
            print(f"{indent}    🔗 Found {len(child_links)} direct child pages")
            
            # Scrape children
            for i, child_url in enumerate(child_links[:15], 1):  # Limit to 15 children
                if len(self.visited_urls) >= self.max_pages:
                    break
                
                print(f"{indent}    [{i}/{min(len(child_links), 15)}]", end=" ")
                child_docs = self.scrape_hierarchical(
                    child_url, 
                    depth=depth + 1,
                    parent_category=category if extracted else parent_category
                )
                documents.extend(child_docs)
        else:
            print(f"{indent}    📝 Leaf page (no children)")
        
        return documents
    
    def scrape_multiple_sections(self, section_urls: List[str]) -> List[Dict]:
        """Scrape multiple top-level sections"""
        print("\n" + "="*70)
        print("🕷️  JAINWORLD HIERARCHICAL SCRAPER (FIXED)")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"  Max Depth: {self.max_depth}")
        print(f"  Max Pages: {self.max_pages}")
        print(f"  Sections: {len(section_urls)}")
        
        all_documents = []
        
        for i, url in enumerate(section_urls, 1):
            print(f"\n{'='*70}")
            print(f"📚 Section {i}/{len(section_urls)}: {url}")
            print("="*70)
            
            docs = self.scrape_hierarchical(url, depth=0)
            all_documents.extend(docs)
            
            print(f"\n{'='*70}")
            print(f"  ✅ Section complete: {len(docs)} documents")
            print(f"  📊 Total so far: {len(all_documents)} documents")
            print(f"  📊 Pages visited: {len(self.visited_urls)}")
            print("="*70)
        
        print("\n" + "="*70)
        print("✅ SCRAPING COMPLETE")
        print("="*70)
        print(f"Total documents: {len(all_documents)}")
        print(f"Total pages visited: {len(self.visited_urls)}")
        print("="*70 + "\n")
        
        return all_documents
    
    def _categorize_content(self, url: str, content: str) -> str:
        """Determine content category"""
        url_lower = url.lower()
        content_lower = content.lower()[:1000]
        
        categories = {
            "stories": ['story', 'tale', 'life of', 'legend', 'narrative'],
            "philosophy": ['philosophy', 'doctrine', 'principle', 'theory', 'concept'],
            "practices": ['practice', 'ritual', 'meditation', 'prayer', 'daily', 'worship'],
            "scriptures": ['scripture', 'agama', 'sutra', 'text', 'sacred'],
            "ethics": ['ethics', 'moral', 'virtue', 'conduct', 'vow'],
            "tirthankaras": ['tirthankara', 'jina', 'ford-maker']
        }
        
        for category, keywords in categories.items():
            if any(kw in url_lower or kw in content_lower for kw in keywords):
                return category
        
        return "general"
    
    def _determine_difficulty(self, content: str) -> str:
        """Determine difficulty level"""
        words = content.split()
        if not words:
            return "beginner"
        
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        advanced_keywords = [
            'metaphysical', 'ontological', 'epistemological', 'cosmology',
            'phenomenological', 'transcendental', 'dialectical'
        ]
        advanced_count = sum(1 for kw in advanced_keywords if kw in content.lower())
        
        if avg_word_length > 6 or advanced_count >= 2:
            return "advanced"
        elif avg_word_length > 5:
            return "intermediate"
        else:
            return "beginner"
    
    def _extract_topic(self, title: str, content: str) -> str:
        """Extract main topic"""
        topics = {
            'ahimsa': ['ahimsa', 'non-violence', 'nonviolence'],
            'karma': ['karma', 'karmic', 'karman'],
            'tirthankaras': ['tirthankara', 'mahavira', 'rishabha', 'jina'],
            'anekantavada': ['anekant', 'syadvada', 'multiple perspective', 'multisided'],
            'jiva': ['jiva', 'soul', 'consciousness'],
            'moksha': ['moksha', 'liberation', 'enlightenment', 'kevala'],
            'samayika': ['samayik', 'meditation', 'equanimity'],
            'vows': ['vrat', 'vow', 'anuvratas'],
            'instincts': ['sangna', 'instinct'],
            'passions': ['kashay', 'passion', 'anger', 'pride'],
            'austerities': ['tap', 'austerit', 'penance'],
        }
        
        text = (title + ' ' + content[:500]).lower()
        
        for topic, keywords in topics.items():
            if any(keyword in text for keyword in keywords):
                return topic
        
        return "general"
    
    def save_documents(self, documents: List[Dict], filename: str = "scraped_content.json"):
        """Save scraped documents to file"""
        filepath = SCRAPED_DIR / filename
        SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(documents)} documents to:")
        print(f"   {filepath}")
        
        # Print statistics
        categories = {}
        difficulties = {}
        topics = {}
        for doc in documents:
            cat = doc['metadata']['category']
            diff = doc['metadata']['difficulty']
            topic = doc['metadata']['topic']
            categories[cat] = categories.get(cat, 0) + 1
            difficulties[diff] = difficulties.get(diff, 0) + 1
            topics[topic] = topics.get(topic, 0) + 1
        
        print(f"\n📊 Statistics:")
        print(f"   Categories: {dict(categories)}")
        print(f"   Difficulties: {dict(difficulties)}")
        print(f"   Topics: {dict(topics)}")
        print(f"   Total words: {sum(d['metadata']['word_count'] for d in documents):,}")
        print(f"   Avg words/doc: {sum(d['metadata']['word_count'] for d in documents) // len(documents) if documents else 0}")
        
        # Show depth distribution
        depths = {}
        for doc in documents:
            d = doc['metadata']['depth']
            depths[d] = depths.get(d, 0) + 1
        print(f"   Depth distribution: {dict(sorted(depths.items()))}")
        
        return filepath


def scrape_jainworld():
    """
    Main scraping function
    Scrapes philosophy section with proper hierarchy
    """
    # Initialize scraper
    scraper = JainWorldHierarchicalScraper(
        max_depth=10,      # main -> subtopic -> sub-subtopic -> leaf
        max_pages=50      # Reasonable limit for demo
    )
    
    # Define sections to scrape
    sections_to_scrape = [
        "https://jainworld.com/philosophy/",
        # Uncomment to add more sections:
        # "https://jainworld.com/education/",
        # "https://jainworld.com/scriptures/",
    ]
    
    # Scrape all sections
    documents = scraper.scrape_multiple_sections(sections_to_scrape)
    
    # Save results
    if documents:
        scraper.save_documents(documents, "learning_modules.json")
    else:
        print("⚠️  No documents scraped!")
    
    return documents


if __name__ == "__main__":
    print("\n" + "="*70)
    print("JAINWORLD.COM HIERARCHICAL SCRAPER")
    print("="*70)
    print("\nFIXES:")
    print("  ✅ Removes URL fragments (#content, etc.)")
    print("  ✅ Only scrapes direct children (no siblings)")
    print("  ✅ Proper depth tracking")
    print("  ✅ Better content extraction")
    print("\nThis will scrape:")
    print("  Level 0: /philosophy/")
    print("  Level 1: /philosophy/ahimsa-non-violence/")
    print("  Level 2: /philosophy/ahimsa-non-violence/introduction/")
    print("  Level 3: Leaf pages")
    print("\nEstimated time: 2-3 minutes")
    print("="*70)
    
    input("\nPress Enter to start scraping...")
    
    documents = scrape_jainworld()
    
    print("\n✅ Done! Next step:")
    print("   python -m scripts.populate_db")