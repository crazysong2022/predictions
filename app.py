import streamlit as st
from modules.auth import login_page
from datetime import datetime, timedelta
from contextlib import closing
import json
import os
import psycopg2

# ==== 导入采集函数 ====
from data_sources import get_fetch_function

# ==== 导入 Polymarket 渲染器 ====
from renderers import polymarket_renderer

# ==== 导入评论模块 ====
from modules.comments import display_comments_section

# ===== 页面配置 =====
st.set_page_config(page_title="🔍 多源事件数据浏览器", layout="wide")

# ===== 登录检查 =====
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    login_page()
    st.stop()

# 获取当前用户角色和ID
user_role = st.session_state.get('role', 'user')
user_id = st.session_state.get('user_id')  # 假设登录后存储了user_id

# ===== 页面标题 =====
st.title("🔍 多源事件数据浏览器")

# ===== 数据库连接与主逻辑 =====
try:
    from utils.db_utils import get_db_connection

    with closing(get_db_connection()) as conn:
        # 查询所有分类
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT categories FROM contents ORDER BY categories;")
            categories = [row[0] for row in cur.fetchall()]

        if not categories:
            st.warning("数据库中没有可用内容")
            st.stop()

        # 使用 tabs 显示不同分类
        tabs = st.tabs(categories)

        for tab, category in zip(tabs, categories):
            with tab:
                # 查询分类下的所有事件
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT slug, title, lists, apis FROM contents WHERE categories = %s ORDER BY slug;",
                        (category,)
                    )
                    rows = cur.fetchall()

                if not rows:
                    st.info(f"分类 {category} 下暂无事件")
                    continue

                for slug, title, lists_data, api_source in rows:
                    with st.expander(f"📎 {title or slug}"):
                        # 解析事件数据
                        try:
                            if isinstance(lists_data, str):
                                event_data = json.loads(lists_data)
                            else:
                                event_data = lists_data

                            if not isinstance(event_data, dict):
                                st.error("❌ 数据格式错误")
                                continue

                        except Exception as e:
                            st.error(f"❌ 解析数据失败：{e}")
                            continue

                        # 查询上次刷新时间
                        with conn.cursor() as cur:
                            cur.execute("SELECT updated_time FROM contents WHERE slug = %s", (slug,))
                            updated_time_row = cur.fetchone()

                        updated_time = updated_time_row[0] if updated_time_row else None

                        # 处理时区（确保无时区比较）
                        if updated_time and updated_time.tzinfo:
                            updated_time = updated_time.replace(tzinfo=None)

                        now = datetime.now().replace(tzinfo=None)
                        six_hours_ago = now - timedelta(hours=6)

                        # 判断是否需要刷新
                        is_recently_updated = updated_time is not None and updated_time > six_hours_ago
                        button_label = f"🕒 {updated_time.strftime('%Y-%m-%d %H:%M')}" if is_recently_updated else "🔄 刷新事件"
                        button_disabled = is_recently_updated
                        button_type = "secondary" if is_recently_updated else "primary"

                        # 刷新按钮（仅限管理员）
                        if user_role == "admin" and api_source:
                            fetch_func = get_fetch_function(api_source)

                            if st.button(
                                button_label,
                                key=f"refresh_{slug}",
                                disabled=button_disabled,
                                type=button_type,
                                use_container_width=True
                            ):
                                with st.spinner(f"🔄 正在从 {api_source} 获取最新数据..."):
                                    fresh_event = fetch_func(slug)

                                    if fresh_event:
                                        with closing(get_db_connection()) as conn_update:
                                            with conn_update.cursor() as cur_update:
                                                cur_update.execute("""
                                                    UPDATE contents 
                                                    SET lists = %s, updated_time = %s
                                                    WHERE slug = %s
                                                """, (
                                                    json.dumps(fresh_event, ensure_ascii=False),
                                                    datetime.now(),
                                                    slug
                                                ))
                                                conn_update.commit()

                                        st.success("✅ 已更新事件数据")
                                        event_data = fresh_event
                                    else:
                                        st.warning("⚠️ 无法获取最新数据")

                        # 动态选择渲染器并展示事件内容
                        if api_source == "polymarket":
                            polymarket_renderer.display_event(event_data)
                        else:
                            st.info("⚠️ 当前数据源暂不支持展示")
                        
                        # 添加评论区，使用事件title作为关联键
                        st.divider()
                        display_comments_section(event_title=title, user_id=user_id)

except Exception as e:
    st.error(f"应用运行错误：{str(e)}")