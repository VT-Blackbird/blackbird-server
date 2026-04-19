import re
import html
from langdetect import DetectorFactory, detect
from bs4 import BeautifulSoup


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

        # 1. Decode HTML entities immediately
        text = html.unescape(raw_text)

        # --- PRE-EXTRACT FALLBACK DATA (important) ---
        alt_match = re.search(r'alt="([^"]+)"', text)
        title_match = re.search(r'title="([^"]+)"', text)

        alt_text = alt_match.group(1) if alt_match else ""
        title_text = title_match.group(1) if title_match else ""

        # 2. Strategy A: Try to find the Content Markers
        marker_pattern = r"SC_OFF(.*?)SC_ON"
        match = re.search(marker_pattern, text, re.DOTALL)

        if match:
            text = match.group(1)
        else:
            # Strip tags as fallback
            text = re.sub(r"<[^>]+>", " ", text)

        # 3. Remove boilerplate
        text = re.sub(r"submitted by\s+\S+", "", text)
        text = re.sub(r"/u/\S+", "", text)
        text = re.sub(r"r/\S+", "", text)
        text = re.sub(r"\[link\]|\[comments\]", "", text, flags=re.IGNORECASE)

        # 4. Cleanup
        text = re.sub(r"\bhref=\S+", "", text)
        text = re.sub(r"\bto\s+", " ", text)

        text = text.strip()
        text = re.sub(r"\s+", " ", text)

        # --- FINAL FALLBACK (NEW) ---
        if not text:
            if alt_text:
                return alt_text.strip()
            if title_text:
                return title_text.strip()

        return text