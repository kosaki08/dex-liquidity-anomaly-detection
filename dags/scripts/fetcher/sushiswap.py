from pathlib import Path
from typing import Any, Dict

from .base import BaseFetcher
from .config import load_protocol_config

_SUSHI_QUERY = (
    Path(__file__).parent / "queries" / "sushiswap_poolHourDatas.gql"
).read_text(encoding="utf-8")


def build_sushiswap_fetcher() -> BaseFetcher:
    """
    Build a SushiSwap fetcher.
    """
    cfg: Dict[str, Any] = load_protocol_config()["sushiswap"]
    endpoint: str = cfg["endpoint_template"].format(
        api_key=cfg["api_key"], subgraph_id=cfg["subgraph_id"]
    )
    headers: Dict[str, str] = {"Authorization": f"Bearer {cfg['api_key']}"}
    return BaseFetcher("sushiswap", endpoint, _SUSHI_QUERY, cfg["page_size"], headers)
