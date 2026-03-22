import re

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