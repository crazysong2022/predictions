# renderers/polymarket_renderer.py

import streamlit as st
import json
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_DESCRIPTION_COUNTER = 0


def safe_float(value, default=0.0):
    """安全地将值转换为浮点数，处理 None 和非数值类型"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_number(value):
    """将数字格式化为 K/M/B 单位"""
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    elif value >= 1e6:
        return f"${value / 1e6:.1f}M"
    elif value >= 1e3:
        return f"${value / 1e3:.1f}K"
    else:
        return f"${value:.0f}"


def format_date(date_str):
    """格式化日期字符串，处理可能的空值"""
    if not date_str:
        return "未知"
    try:
        # 假设日期格式为 "2024-12-31T20:51:43.447192Z"
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return date_str  # 保持原始格式如果解析失败


def create_volume_dataframe(vol_24hr, vol_1wk, vol_1mo, vol_1yr):
    """创建用于 st.bar_chart 的 DataFrame"""
    data = {
        "时间段": ["24小时", "1周", "1月", "1年"],
        "成交量 (USD)": [vol_24hr, vol_1wk, vol_1mo, vol_1yr]
    }
    return pd.DataFrame(data).set_index("时间段")


def display_market(market):
    icon = market.get("icon", "")
    volume = safe_float(market.get("volume"))
    liquidity = safe_float(market.get("liquidity"))
    best_bid = safe_float(market.get("bestBid"))
    best_ask = safe_float(market.get("bestAsk"))
    last_price = safe_float(market.get("lastTradePrice"))
    closed = market.get("closed", False)

    outcome_prices = market.get("outcomePrices")
    if outcome_prices is None:
        outcome_prices = "[0, 0]"  # 默认值，避免解析 None
    try:
        outcome_prices = json.loads(outcome_prices)
    except json.JSONDecodeError:
        outcome_prices = [0, 0]
    yes_prob = float(outcome_prices[0]) if len(outcome_prices) > 0 else 0
    no_prob = float(outcome_prices[1]) if len(outcome_prices) > 1 else 0

    vol_24hr = safe_float(market.get("volume24hr"))
    vol_1wk = safe_float(market.get("volume1wk"))
    vol_1mo = safe_float(market.get("volume1mo"))
    vol_1yr = safe_float(market.get("volume1yr"))

    status_icon = "🟢" if not closed else "🔴"
    st.markdown(f"### {status_icon} 市场详情")

    col1, col2 = st.columns([1, 3])
    with col1:
        if icon:
            st.image(icon, width=80)
    with col2:
        st.markdown(f"💰 最新成交价：**${last_price:.2f}**")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="📈 总交易量 (USD)", value=format_number(volume))
        st.metric(label="🛒 最高买价 (Best Bid)", value=f"${best_bid:.2f}")
    with col2:
        st.metric(label="💧 流动性池 (USD)", value=format_number(liquidity))
        st.metric(label="💵 最低卖价 (Best Ask)", value=f"${best_ask:.2f}")

    st.markdown("🎯 预测概率分布：")
    st.progress(yes_prob)
    st.markdown(f"- **Yes**: {yes_prob * 100:.1f}%")
    st.progress(no_prob)
    st.markdown(f"- **No**: {no_prob * 100:.1f}%")

    st.markdown("📊 时间段成交量分布：")
    df = create_volume_dataframe(vol_24hr, vol_1wk, vol_1mo, vol_1yr)
    st.bar_chart(df, use_container_width=True)

    st.markdown("---")


def display_event(event_data):
    """
    Polymarket 事件专用渲染器
    根据 event 数据渲染完整的事件 + 市场信息
    """
    logger.info("Rendering Polymarket event data")

    slug = event_data.get("slug", "无 Slug")
    icon = event_data.get("icon", "")
    description = event_data.get("description", "暂无描述").strip() or "暂无描述"
    closed = event_data.get("closed", False)
    start_date = format_date(event_data.get("startDate"))
    end_date = format_date(event_data.get("endDate"))

    volume = safe_float(event_data.get("volume"))
    liquidity = safe_float(event_data.get("liquidity"))

    vol_24hr = safe_float(event_data.get("volume24hr"))
    vol_1wk = safe_float(event_data.get("volume1wk"))
    vol_1mo = safe_float(event_data.get("volume1mo"))
    vol_1yr = safe_float(event_data.get("volume1yr"))

    markets = event_data.get("markets", [])
    active_markets = [m for m in markets if not m.get("closed", False)]
    closed_markets = [m for m in markets if m.get("closed", True)]

    with st.container():
        col1, col2 = st.columns([1, 4])
        with col1:
            if icon:
                st.image(icon, width=80)
        with col2:
            status_icon = "🟢" if not closed else "🔴"
            st.markdown(f"### {status_icon} 事件状态：{'已关闭' if closed else '进行中'}")
            st.markdown(f"📅 开始时间：{start_date}")
            st.markdown(f"🔚 结束时间：{end_date}")

        st.markdown("---")

        st.markdown("### 💰 交易数据概览")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="📈 总交易量 (USD)", value=format_number(volume))
        with col2:
            st.metric(label="💧 流动性池 (USD)", value=format_number(liquidity))

        st.markdown("---")

        st.markdown("### 📊 时间段成交量统计")
        df = create_volume_dataframe(vol_24hr, vol_1wk, vol_1mo, vol_1yr)
        st.bar_chart(df, use_container_width=True)

        st.markdown("---")

        if active_markets:
            st.markdown("### 🔍 活跃市场（未关闭）")
            tab_labels = [m.get("groupItemTitle", f"未知市场 {i+1}") for i, m in enumerate(active_markets)]
            tabs = st.tabs(tab_labels)
            for tab, market in zip(tabs, active_markets):
                with tab:
                    display_market(market)

        if closed_markets:
            st.markdown("### 🔚 已关闭市场（历史参考）")
            tab_labels = [m.get("groupItemTitle", f"未知市场 {i+1}") for i, m in enumerate(closed_markets)]
            tabs = st.tabs(tab_labels)
            for tab, market in zip(tabs, closed_markets):
                with tab:
                    display_market(market)