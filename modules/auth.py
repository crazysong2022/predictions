# modules/auth.py
import streamlit as st
from utils.db_utils import get_db_connection
from contextlib import closing
import bcrypt


def connect_db():
    """使用统一的数据库连接函数"""
    return get_db_connection()


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def login_form():
    st.subheader("🔐 登录")
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submit = st.form_submit_button("登录")

        if submit:
            try:
                with closing(get_db_connection()) as conn:
                    with conn.cursor() as cur:
                        # ✅ 改成查询 id, password_hash, role
                        cur.execute("SELECT id, password_hash, role FROM users WHERE username = %s", (username,))
                        result = cur.fetchone()
                        if result:
                            user_id, hashed, role = result  # ✅ 获取到 user_id
                            if check_password(password, hashed):
                                st.session_state['logged_in'] = True
                                st.session_state['username'] = username
                                st.session_state['role'] = role
                                st.session_state['user_id'] = user_id  # ✅ 添加这一行
                                st.success(f"欢迎回来，{username}！")
                                st.rerun()
                            else:
                                st.error("密码错误")
                        else:
                            st.error("用户名不存在")
            except Exception as e:
                st.error(f"登录失败：{str(e)}")


def register_form():
    st.subheader("📝 注册新用户")
    with st.form("register_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        confirm_password = st.text_input("确认密码", type="password")
        submit = st.form_submit_button("注册")

        if submit:
            if not username or not password:
                st.warning("请输入用户名和密码")
            elif password != confirm_password:
                st.warning("两次输入的密码不一致")
            else:
                try:
                    with closing(get_db_connection()) as conn:
                        with conn.cursor() as cur:

                            # 调试信息：查看当前数据库用户数
                            cur.execute("SELECT COUNT(*) FROM users;")
                            total_users = cur.fetchone()[0]
                            st.write("📊 当前用户总数:", total_users)

                            # 检查用户名是否存在
                            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                            if cur.fetchone():
                                st.error("该用户名已被占用")
                            else:
                                hashed = hash_password(password)
                                cur.execute(
                                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                                    (username, hashed)
                                )
                                conn.commit()
                                st.success("✅ 注册成功，请登录")

                except Exception as e:
                    conn.rollback()
                    st.error(f"注册失败：{str(e)}")


def logout():
    st.session_state.clear()
    st.info("您已成功登出")
    st.rerun()


def login_page():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        st.sidebar.success(f"当前用户：{st.session_state['username']} ({st.session_state['role']})")
        if st.sidebar.button("🚪 登出"):
            logout()
        return

    st.sidebar.title("请登录")
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        login_form()
    with tab2:
        register_form()