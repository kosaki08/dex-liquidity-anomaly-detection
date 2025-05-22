from datetime import datetime, timezone

import responses

from scripts.fetcher.uniswap import build_uniswap_fetcher


def _graph_response() -> dict:
    """The Graph API のダミーレスポンス 1 件分"""
    return {
        "data": {
            "poolHourDatas": [
                {
                    "id": "1",
                    "periodStartUnix": int(datetime.now(tz=timezone.utc).timestamp()),
                    "liquidity": "123",
                    "volumeUSD": "456",
                    # …必要最小限のフィールドだけ用意
                }
            ]
        }
    }


@responses.activate
def test_fetch_interval_single_page(tmp_path):
    fetcher = build_uniswap_fetcher()

    # 全リクエストをダミーで返す
    responses.add(
        responses.POST,
        fetcher.endpoint,
        json=_graph_response(),
        status=200,
    )

    recs = fetcher.fetch_interval(datetime.now(tz=timezone.utc).isoformat())
    assert len(recs) == 1
    assert recs[0]["id"] == "1"

    out = tmp_path / "out.jsonl"
    fetcher.save(recs, out)
    assert out.exists()
    # JSONL 1 行だけか確認
    assert sum(1 for _ in out.open()) == 1
    assert sum(1 for _ in out.open()) == 1
