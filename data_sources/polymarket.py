# data_sources/polymarket.py

import requests
from urllib.parse import quote
import json

def fetch_polymarket_event(slug):
    """
    从 Polymarket 获取事件数据（通过 slug）
    """
    base_url = "https://gamma-api.polymarket.com/events"
    headers = {"User-Agent": "MultiSourceEventBrowser/1.0"}

    try:
        response = requests.get(
            f"{base_url}?slug={quote(slug)}",
            headers=headers,
            timeout=10  # 加上超时
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return extract_relevant_fields(data[0])
            else:
                print(f"[Polymarket] 未找到事件数据，slug={slug}")
        else:
            print(f"[Polymarket] 请求失败，状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[Polymarket] 网络请求失败: {e}")
    except json.JSONDecodeError:
        print("[Polymarket] 响应内容不是有效的 JSON")
    except Exception as e:
        print(f"[Polymarket] 未知错误: {e}")

    return None

def extract_relevant_fields(event):
    """提取最小字段集合"""
    markets = []
    for m in event.get("markets", []):
        markets.append({
            "icon": m.get("icon"),
            "volume": m.get("volume"),
            "liquidity": m.get("liquidity"),
            "bestBid": m.get("bestBid"),
            "bestAsk": m.get("bestAsk"),
            "lastTradePrice": m.get("lastTradePrice"),
            "closed": m.get("closed"),
            "outcomePrices": m.get("outcomePrices"),
            "groupItemTitle": m.get("groupItemTitle"),
            "volume24hr": m.get("volume24hr", 0),
            "volume1wk": m.get("volume1wk", 0),
            "volume1mo": m.get("volume1mo", 0),
            "volume1yr": m.get("volume1yr", 0)
        })

    return {
        "slug": event.get("slug"),
        "icon": event.get("icon"),
        "description": event.get("description"),
        "closed": event.get("closed"),
        "startDate": event.get("startDate"),
        "endDate": event.get("endDate"),
        "volume": event.get("volume"),
        "liquidity": event.get("liquidity"),
        "volume24hr": event.get("volume24hr", 0),
        "volume1wk": event.get("volume1wk", 0),
        "volume1mo": event.get("volume1mo", 0),
        "volume1yr": event.get("volume1yr", 0),
        "title": event.get("title", ""),
        "markets": markets
    }