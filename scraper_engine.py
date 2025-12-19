import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_rss_entries(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(resp.content)
        return feed.entries if feed.entries else []
    except: return []

def extract_links_for_crawler(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.content, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            href = urljoin(url, a['href'])
            if len(text) > 2:
                links.append(f"TEXT: {text} | LINK: {href}")
        return "\n".join(links[:150]) 
    except:
        return None
