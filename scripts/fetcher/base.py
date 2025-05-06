import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .types import PoolHourData


class BaseFetcher:
    """
    Base class for fetching data from a GraphQL endpoint.
    """

    def __init__(
        self,
        name,
        endpoint,
        query: str,
        page_size: int,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the BaseFetcher.
        """
        self.name: str = name
        self.endpoint: str = endpoint
        self.query: str = query
        self.page_size: int = page_size
        self.headers: Dict[str, str] = headers or {}

    def fetch_interval(self, interval_end_iso: str) -> List[PoolHourData]:
        """
        Fetch data for a specific time interval.
        """
        # 1時間前を start／end timestamp に変換
        end_dt = datetime.fromisoformat(interval_end_iso.replace("Z", "+00:00"))
        start_dt = end_dt - timedelta(hours=1)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())

        all_records: List[PoolHourData] = []
        skip = 0
        while True:
            variables: Dict[str, Any] = {
                "startTime": start_ts,
                "endTime": end_ts,
                "first": self.page_size,
                "skip": skip,
            }
            logging.info(f"[{self.name}] fetch skip={skip}")
            resp = requests.post(
                self.endpoint,
                json={"query": self.query, "variables": variables},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                raise RuntimeError(data["errors"])
            page = data["data"]["poolHourDatas"]
            if not page:
                break
            all_records.extend(page)
            if len(page) < self.page_size:
                break
            skip += self.page_size
        return all_records

    def save(self, records: List[PoolHourData], output_path: str) -> None:
        """
        Save the fetched data to a file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logging.info(f"[{self.name}] saved {len(records)} to {output_path}")

    def run(self, output_path: str, interval_end_iso: str) -> None:
        """
        Run the fetcher.
        """
        recs = self.fetch_interval(interval_end_iso)
        self.save(recs, output_path)
