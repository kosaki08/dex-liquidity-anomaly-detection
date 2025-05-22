from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class SnowflakeConfig(BaseSettings):
    user: str = Field(..., env="SNOWFLAKE_USER")
    password: str = Field(..., env="SNOWFLAKE_PASSWORD")
    account: str = Field(..., env="SNOWFLAKE_ACCOUNT")
    warehouse: str = Field(..., env="SNOWFLAKE_WAREHOUSE")
    database: str = Field(..., env="SNOWFLAKE_DATABASE")

    # pydantic-settings の BaseSettings には schema が定義されているため、
    # 衝突回避のため schema → sf_schema に変更
    sf_schema: str = Field(..., alias="schema", env="SNOWFLAKE_SCHEMA")
    role: str = Field(..., env="SNOWFLAKE_ROLE")

    model_config = {
        "env_file": ".env",
        "populate_by_name": True,  # alias 名でも環境変数 → attr 参照可
    }

    # ---------- 互換用エイリアス (読み取り専用) ----------
    @computed_field
    @property
    def schema(self) -> str:  # type: ignore[override]  # mypy 上書き警告を抑制
        """`sf_schema` のエイリアスです。書き込みできません"""
        return self.sf_schema
