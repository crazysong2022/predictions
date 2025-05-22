# renderers/default_renderer.py
import streamlit as st

def display_event(event_data):
    """
    默认渲染器：以 JSON 形式展示原始数据
    """
    st.markdown("### ⚪ 未知数据源（默认渲染）")
    st.json(event_data)