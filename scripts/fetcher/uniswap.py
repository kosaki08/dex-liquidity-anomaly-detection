from pathlib import Path
from typing import Any, Dict

from .base import BaseFetcher
from .config import load_protocol_config

_UNI_QUERY = (
    Path(__file__).parent / "queries" / "uniswap_poolHourDatas.gql"
).read_text()


def build_uniswap_fetcher() -> BaseFetcher:
    """
    Build a Uniswap fetcher.
    """
    cfg: Dict[str, Any] = load_protocol_config()["uniswap"]
    endpoint: str = cfg["endpoint_template"].format(
        api_key=cfg["api_key"], subgraph_id=cfg["subgraph_id"]
    )
    return BaseFetcher("uniswap", endpoint, _UNI_QUERY, cfg["page_size"])
