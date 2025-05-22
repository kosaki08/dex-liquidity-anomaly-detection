from pydantic import Field
from pydantic_settings import BaseSettings


class SnowflakeConfig(BaseSettings):
    user: str = Field(..., env="SNOWFLAKE_USER")
    password: str = Field(..., env="SNOWFLAKE_PASSWORD")
    account: str = Field(..., env="SNOWFLAKE_ACCOUNT")
    warehouse: str = Field(..., env="SNOWFLAKE_WAREHOUSE")
    database: str = Field(..., env="SNOWFLAKE_DATABASE")
    schema: str = Field(..., env="SNOWFLAKE_SCHEMA")
    role: str = Field(..., env="SNOWFLAKE_ROLE")

    class Config:
        env_file = ".env"
        env_file = ".env"
