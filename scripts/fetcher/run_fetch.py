import logging
from datetime import datetime

from .sushiswap import build_sushiswap_fetcher
from .types import ProtocolName
from .uniswap import build_uniswap_fetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def fetch_pool_data(protocol: ProtocolName, output_path: str, data_interval_end: str) -> None:
    """
    Common entry point called from Airflow's PythonOperator
    """
    logging.info(f"START fetch_pool_data: protocol={protocol}, interval_end={data_interval_end}, output={output_path}")

    if protocol == "uniswap":
        fetcher = build_uniswap_fetcher()
    elif protocol == "sushiswap":
        fetcher = build_sushiswap_fetcher()
    else:
        raise ValueError(f"Unknown protocol: {protocol}")
    fetcher.run(output_path, data_interval_end)
    logging.info(f"END   fetch_pool_data: protocol={protocol}")


if __name__ == "__main__":
    """
    Local execution example
    """
    from datetime import timezone

    dt_end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()

    # Uniswap
    run = build_uniswap_fetcher()
    run.run(f"./data/raw/{dt_end[:10]}_uni.jsonl", dt_end)

    # SushiSwap
    run = build_sushiswap_fetcher()
    run.run(f"./data/raw/{dt_end[:10]}_sushi.jsonl", dt_end)
