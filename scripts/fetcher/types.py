from typing import Literal, TypedDict

ProtocolName = Literal["uniswap", "sushiswap"]


class ProtocolConfig(TypedDict):
    api_key: str
    subgraph_id: str
    endpoint_template: str
    page_size: int


class ProtocolConfigMap(TypedDict):
    uniswap: ProtocolConfig
    sushiswap: ProtocolConfig


class TokenInfo(TypedDict):
    id: str
    symbol: str
    name: str
    decimals: str


class PoolInfo(TypedDict):
    id: str
    token0: TokenInfo
    token1: TokenInfo
    # feeTier は V3 のみ存在
    feeTier: str


class PoolHourData(TypedDict):
    id: str
    periodStartUnix: int
    pool: PoolInfo
    liquidity: str
    sqrtPrice: str
    token0Price: str
    token1Price: str
    tick: str
    feeGrowthGlobal0X128: str
    feeGrowthGlobal1X128: str
    tvlUSD: str
    volumeToken0: str
    volumeToken1: str
    volumeUSD: str
    feesUSD: str
    txCount: str
    open: str
    high: str
    low: str
    close: str
