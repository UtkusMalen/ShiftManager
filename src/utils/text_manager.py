import yaml
from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

TEXTS_FILE = Path(__file__).parent / "locales" / "texts.yaml"

class TextManager:
    def __init__(self, file_path: Path = TEXTS_FILE):
        self.file_path = file_path
        self.texts = self._load_texts()

    def _load_texts(self) -> dict:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logging.error(f"Failed to load texts from {self.file_path}: {e}")
            return {}

    def get(self, key: str, default: Optional[Any] = None, **kwargs) -> str:
        keys = key.split(".")
        value = self.texts
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                logger.warning(f"Key {key} not found in texts, missing {k}")
                return default

        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing key for formatting text {key}: {e}")
                return value
        else:
            logger.warning(f"Value for key {key} is not a string")
            return value if value is not None else default

text_manager = TextManager()

