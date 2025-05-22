# data_sources/__init__.py

from .polymarket import fetch_polymarket_event

# 支持的数据源名称 → 对应采集函数
SOURCE_FUNCTIONS = {
    "polymarket": fetch_polymarket_event,
    # "example_api": fetch_example_api_event,
}

def get_fetch_function(source_name):
    return SOURCE_FUNCTIONS.get(source_name)