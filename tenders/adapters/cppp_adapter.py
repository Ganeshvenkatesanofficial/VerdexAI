import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from .base import BaseTenderAdapter

IST = pytz.timezone("Asia/Kolkata")


class CPPPAdapter(BaseTenderAdapter):
    source_portal = 'cppp'
    BASE_URL = "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata"

    def __init__(self, max_pages=3):
        # Start small — 3 pages ≈ 30 tenders — increase once this is proven stable
        self.max_pages = max_pages

    def fetch_raw_listings(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (compatible; VerdexBot/1.0; +https://verdex.xyz)"
        }
        all_rows = []

        for page in range(1, self.max_pages + 1):
            params = {"page": page} if page > 1 else {}
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            rows = soup.select("table#table tbody tr")

            if not rows:
                break  # ran out of pages

            all_rows.extend(rows)
            time.sleep(1)  # be polite to a government server — never hammer it

        return all_rows

    def normalize(self, raw_item):
        cells = raw_item.find_all("td")

        published_date_str = cells[1].get_text(strip=True)
        closing_date_str = cells[2].get_text(strip=True)

        title_cell = cells[4]
        link = title_cell.find("a")
        title = link.get_text(strip=True) if link else title_cell.get_text(strip=True)

        full_text = title_cell.get_text(strip=True)
        trailing_text = full_text[len(title):]  # e.g. "/1000464748/2026_BPCL_26648"
        parts = [p for p in trailing_text.split("/") if p]
        tender_id = parts[-1] if parts else title  # fallback if format ever changes

        org_name = cells[5].get_text(strip=True) if len(cells) > 5 else ""

        return {
            "source_portal": self.source_portal,
            "source_tender_id": tender_id,
            "title": title,
            "category": "",  # not exposed in listing — backfill later via detail page or keyword tagging
            "closing_date": self._parse_date(closing_date_str),
            "published_date": self._parse_date(published_date_str),
            "raw_listing_text": raw_item.get_text(separator=" ", strip=True),
        }

    def _parse_date(self, date_str):
        try:
            dt = datetime.strptime(date_str, "%d-%b-%Y %I:%M %p")
            return IST.localize(dt).astimezone(pytz.UTC)
        except (ValueError, TypeError):
            return None
