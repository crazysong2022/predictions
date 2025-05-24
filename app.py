import streamlit as st
from modules.auth import login_page, logout
from datetime import datetime, timedelta, timezone
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


# =================== 辅助函数定义（必须放前面）===================

def show_events_by_category(conn, category, user_role, user_id):
    """显示某个主分类下的所有事件（无子分类）"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT slug, title, lists, apis 
            FROM contents 
            WHERE categories = %s AND sub_category IS NULL 
            ORDER BY slug;
        """, (category,))
        events = cur.fetchall()

    if not events:
        st.info(f"分类 {category} 下暂无事件")
        return

    for slug, title, lists_data, api_source in events:
        render_event_card(slug, title, lists_data, api_source, user_role, user_id, conn)


def show_events_by_sub_category(conn, category, sub_category, user_role, user_id):
    """显示某个子分类下的事件"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT slug, title, lists, apis 
            FROM contents 
            WHERE categories = %s AND sub_category = %s 
            ORDER BY slug;
        """, (category, sub_category))
        events = cur.fetchall()

    if not events:
        st.info(f"子分类 {sub_category} 下暂无事件")
        return

    for slug, title, lists_data, api_source in events:
        render_event_card(slug, title, lists_data, api_source, user_role, user_id, conn)


def render_event_card(slug, title, lists_data, api_source, user_role, user_id, conn):
    """渲染单个事件卡片"""
    with st.expander(f"📎 {title or slug}"):
        try:
            if isinstance(lists_data, str):
                event_data = json.loads(lists_data)
            else:
                event_data = lists_data

            if not isinstance(event_data, dict):
                st.error("❌ 数据格式错误")
                return

        except Exception as e:
            st.error(f"❌ 解析数据失败：{e}")
            return

        # ==== 刷新按钮逻辑（管理员专属）====
        with conn.cursor() as cur:
            cur.execute("SELECT updated_time FROM contents WHERE slug = %s", (slug,))
            updated_time_row = cur.fetchone()

        updated_time = updated_time_row[0] if updated_time_row else None

        # 统一时区为 UTC
        now = datetime.now(timezone.utc)

        if updated_time is not None:
            if updated_time.tzinfo is None:
                # 如果没有时区信息，假设是 UTC
                updated_time = updated_time.replace(tzinfo=timezone.utc)
            else:
                updated_time = updated_time.astimezone(timezone.utc)

        six_hours_ago = now - timedelta(hours=6)
        is_recently_updated = updated_time is not None and updated_time > six_hours_ago

        button_label = f"🕒 {updated_time.strftime('%Y-%m-%d %H:%M')}" if is_recently_updated else "🔄 刷新事件"
        button_disabled = is_recently_updated
        button_type = "secondary" if is_recently_updated else "primary"

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
                        with conn.cursor() as cur_update:
                            cur_update.execute("""
                                UPDATE contents 
                                SET lists = %s, updated_time = %s
                                WHERE slug = %s
                            """, (
                                json.dumps(fresh_event, ensure_ascii=False),
                                datetime.now(timezone.utc),  # 使用带时区的时间
                                slug
                            ))
                            conn.commit()

                        st.success("✅ 已更新事件数据")
                        event_data = fresh_event
                    else:
                        st.warning("⚠️ 无法获取最新数据")

        # ==== 渲染器选择 ====
        if api_source == "polymarket":
            polymarket_renderer.display_event(event_data)
        else:
            st.info("⚠️ 当前数据源暂不支持展示")

        # ==== 评论区 ====
        st.divider()
        display_comments_section(event_title=title, user_id=user_id)


# ===== 初始化会话状态 =====
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

# ===== 从 URL 参数恢复会话状态 =====
query_params = st.query_params
if 'logged_in' in query_params and 'username' in query_params:
    logged_in = query_params['logged_in'] == 'True'
    username = query_params['username']

    # 可选：验证用户是否存在数据库中（提高安全性）
    try:
        from utils.db_utils import get_db_connection
        with closing(get_db_connection()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, role FROM users WHERE username = %s", (username,))
                result = cur.fetchone()
                if result:
                    user_id, role = result
                    st.session_state["logged_in"] = logged_in
                    st.session_state["username"] = username
                    st.session_state["role"] = role
                    st.session_state["user_id"] = user_id
                else:
                    st.session_state["logged_in"] = False
                    st.query_params.clear()
    except Exception as e:
        st.session_state["logged_in"] = False
        st.query_params.clear()

# ===== 页面配置 =====
st.set_page_config(page_title="🔍 多源事件数据浏览器", layout="wide")

# ===== 登录检查 =====
if not st.session_state["logged_in"]:
    login_page()
    st.stop()

# 获取当前用户角色和ID
user_role = st.session_state.get('role', 'user')
user_id = st.session_state.get('user_id')

# ===== 显示欢迎信息 + 登出按钮 =====
col1, col2 = st.columns([10, 1])
with col1:
    st.markdown(f"👋 欢迎回来，{st.session_state['username']} ({st.session_state['role']})")
with col2:
    if st.button("🚪 登出", use_container_width=True, key="logout_button"):
        logout()
        st.rerun()

# 更新 URL 参数以反映当前登录状态
st.query_params.update({
    "logged_in": str(st.session_state["logged_in"]),
    "username": st.session_state["username"]
})

# ===== 页面标题 =====
st.title("🔍 多源事件数据浏览器")

# ===== 数据库连接与主逻辑 =====
try:
    from utils.db_utils import get_db_connection

    with closing(get_db_connection()) as conn:

        # 查询所有主分类及其子分类
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT categories, sub_category 
                FROM contents 
                ORDER BY categories, sub_category NULLS LAST;
            """)
            rows = cur.fetchall()

        # 构建主分类 -> 子分类映射
        category_sub_map = {}
        for category, sub_category in rows:
            if category not in category_sub_map:
                category_sub_map[category] = set()
            if sub_category is not None:
                category_sub_map[category].add(sub_category)

        # 获取所有主分类
        categories = list(category_sub_map.keys())

        if not categories:
            st.warning("数据库中没有可用内容")
            st.stop()

        # 使用 tabs 显示不同分类
        tabs = st.tabs(categories)

        for tab, category in zip(tabs, categories):
            with tab:
                sub_categories = category_sub_map.get(category, set())

                if not sub_categories or None in sub_categories:
                    # 如果没有子分类或只有空子分类，则直接显示该 category 下的所有事件
                    show_events_by_category(conn, category, user_role, user_id)
                else:
                    # 否则用子 tab 分类显示
                    sub_tabs = st.tabs(sorted(sub_categories))
                    for sub_tab, sub_category in zip(sub_tabs, sorted(sub_categories)):
                        with sub_tab:
                            show_events_by_sub_category(conn, category, sub_category, user_role, user_id)

except Exception as e:
    st.error(f"应用运行错误：{str(e)}")