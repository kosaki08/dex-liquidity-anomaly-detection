import os
from pathlib import Path

import yaml

from .types import ProtocolConfigMap


def load_protocol_config() -> ProtocolConfigMap:
    """
    Load the protocol config from the protocols.yml file.
    """

    # 環境変数 or YAMLで定義したprotocols.ymlを読み込み
    # config.py は scripts/fetcher/config.py にあるので、
    # 親(parent)[0]=fetcher, 親(parent)[1]=scripts, 親(parent)[2]=project root
    cfg_path = Path(__file__).resolve().parents[2] / "protocols.yml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"{cfg_path} が見つかりません")

    # Path → 文字列にして safe_load に渡す
    yaml_text = cfg_path.read_text(encoding="utf-8")
    raw: ProtocolConfigMap = yaml.safe_load(yaml_text)

    # 環境変数展開
    for proto, conf in raw.items():
        for k, v in conf.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env = v[2:-1]
                raw[proto][k] = os.getenv(env)
    return raw
