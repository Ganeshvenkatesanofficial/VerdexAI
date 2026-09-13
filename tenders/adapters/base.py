from abc import ABC, abstractmethod


class BaseTenderAdapter(ABC):
    """
    Every portal adapter must implement fetch_and_normalize(),
    returning a list of dicts matching the canonical Tender shape.
    """

    source_portal = None  # override in subclass, e.g. 'gem' or 'cppp'

    @abstractmethod
    def fetch_raw_listings(self):
        """Fetch raw data from the portal. Returns portal-specific raw data."""
        pass

    @abstractmethod
    def normalize(self, raw_item):
        """Convert one raw portal item into the canonical Tender dict shape."""
        pass

    def fetch_and_normalize(self):
        raw_items = self.fetch_raw_listings()
        normalized = []
        for item in raw_items:
            try:
                normalized.append(self.normalize(item))
            except Exception as e:
                print(f"[{self.source_portal}] Failed to normalize item: {e}")
        return normalized
