import html
import re

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect

# Ensures consistent results across runs
DetectorFactory.seed = 0


class DataCleaner:
    def is_english(self, text: str) -> bool:
        """Checks if the provided text is English."""
        try:
            # Language detection works best on a decent amount of text
            if len(text) < 20:
                return True  # Too short to reliably detect, assume OK

            return bool(detect(text) == 'en')
        except Exception:
            # If detection fails (e.g., only emojis/numbers), treat as non-English
            return False

    def clean(self, text: str) -> str:
        """Cleans the entire text for DB storage."""
        if not text:
            return ""

        # 1. Strip Noise
        text = re.sub(r'https?://\S+|www\.\S+|<.*?>', '', text)

        # 2. Fix Formatting
        text = text.replace("...", " ")
        text = " ".join(text.split())

        return text

    @staticmethod
    def clean_reddit_content(raw_text: str) -> str:
        if not raw_text:
            return ""



        # 1. Decode HTML entities
        raw_text = html.unescape(raw_text)

        # 2. Parse HTML properly
        soup = BeautifulSoup(raw_text, "html.parser")

        img_alt = None
        img_title = None

        img = soup.find("img")
        if img:
            img_alt = img.get("alt")
            img_title = img.get("title")

        # 3. Focus on actual Reddit content
        md_div = soup.find("div", class_="md")

        if md_div:
            soup = md_div  # isolate main content

        # 4. Remove junk elements
        for tag in soup(["script", "style", "img", "table"]):
            tag.decompose()

        # Remove reddit navigation / metadata links
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if "reddit.com" in href:
                a.decompose()

        # 5. Extract structured text
        lines = []
        for el in soup.find_all(["p", "li", "blockquote", "h1", "h2", "h3"]):
            text = el.get_text(" ", strip=True)
            if text:
                lines.append(text)

        text = "\n".join(lines)

        # 6. Cleanup (keep your good regex work here)
        text = re.sub(r'\[link\]|\[comments\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'submitted by\s+\S+', '', text)
        text = re.sub(r'/u/\S+', '', text)
        text = re.sub(r'r/\S+', '', text)

        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            text = (img_alt or img_title or "").strip()

        return text