import streamlit as st
from utils.db_utils import get_db_connection


def create_comment(user_id, content, parent_id=None, event_title=None):
    """创建评论并关联到特定内容"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO comments (user_id, content, parent_id, title, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    RETURNING id
                """, (user_id, content, parent_id, event_title))
                comment_id = cur.fetchone()[0]
                conn.commit()
                return comment_id
    except Exception as e:
        st.error(f"提交评论失败: {str(e)}")
        return None


def like_comment(comment_id):
    """为指定评论点赞"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE comments 
                    SET likes = likes + 1 
                    WHERE id = %s
                    RETURNING likes
                """, (comment_id,))
                new_likes = cur.fetchone()[0]
                conn.commit()
                return new_likes
    except Exception as e:
        st.error(f"点赞失败: {str(e)}")
        return None


def get_comments(event_title):
    """获取特定内容的所有评论（包括回复）"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    WITH RECURSIVE comment_tree AS (
                        SELECT 
                            c.id, c.user_id, u.username, c.content, c.parent_id, c.title, c.likes, c.created_at, 0 AS depth
                        FROM comments c
                        JOIN users u ON c.user_id = u.id
                        WHERE c.title = %s AND c.parent_id IS NULL
                        
                        UNION ALL
                        
                        SELECT 
                            c.id, c.user_id, u.username, c.content, c.parent_id, c.title, c.likes, c.created_at, ct.depth + 1
                        FROM comments c
                        JOIN users u ON c.user_id = u.id
                        JOIN comment_tree ct ON c.parent_id = ct.id
                    )
                    SELECT id, user_id, username, content, parent_id, title, likes, created_at, depth
                    FROM comment_tree
                    ORDER BY created_at ASC;
                """, (event_title,))
                return cur.fetchall()
    except Exception as e:
        st.error(f"加载评论失败: {str(e)}")
        return []


def display_comments_section(event_title, user_id):
    """显示评论区组件"""
    st.subheader("💬 讨论区")

    # 评论输入表单
    with st.form(key=f"comment_form_{event_title}"):
        comment_text = st.text_area("写下你的评论...", height=100)
        submitted = st.form_submit_button("发布评论")

        if submitted:
            if not comment_text.strip():
                st.warning("评论内容不能为空")
            elif not user_id:
                st.error("❌ 用户未登录，无法发表评论")
            else:
                comment_id = create_comment(user_id, comment_text, event_title=event_title)
                if comment_id:
                    st.success("✅ 评论已提交！")
                    st.rerun()
                else:
                    st.error("提交评论失败，请重试")

    # 加载并显示评论
    comments = get_comments(event_title)

    if not comments:
        st.info("还没有评论，快来发起讨论吧！")
    else:
        # 构建评论树结构
        comment_dict = {}
        for row in comments:
            comment_id, _, username, content, parent_id, _, likes, created_at, depth = row
            comment_dict[comment_id] = {
                "username": username,
                "content": content,
                "likes": likes,
                "created_at": created_at,
                "depth": depth,
                "replies": []
            }

        # 建立父子关系
        root_comments = []
        for comment_id, data in comment_dict.items():
            parent_id = comments[[c[0] for c in comments].index(comment_id)][4]
            if parent_id is None:
                root_comments.append(comment_id)
            else:
                if parent_id in comment_dict:
                    comment_dict[parent_id]["replies"].append(comment_id)

        # 初始化 session_state 控制展开状态
        if 'reply_forms' not in st.session_state:
            st.session_state.reply_forms = {}

        def toggle_reply_form(cid):
            st.session_state.reply_forms[cid] = not st.session_state.reply_forms.get(cid, False)

        # 渲染评论树函数
        def render_comment_tree(comment_ids, depth=0):
            for comment_id in comment_ids:
                comment = comment_dict[comment_id]

                # 显示评论卡片
                st.markdown(f"""
                    <div style="border-left: 3px solid #e2e8f0; padding-left: 1rem; margin-bottom: 1rem; margin-left: {depth * 1}rem;">
                        <strong>{comment['username']}</strong> 
                        <small style="color: #64748b;">{comment['created_at'].strftime('%Y-%m-%d %H:%M')}</small>
                        <p>{comment['content']}</p>
                    </div>
                """, unsafe_allow_html=True)

                # 点赞按钮和回复按钮布局
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button(f"❤️ {comment['likes']}", key=f"like_{comment_id}"):
                        new_likes = like_comment(comment_id)
                        if new_likes is not None:
                            st.success("已点赞！💖")
                            st.rerun()

                with col2:
                    if st.button("🗨️ 回复", key=f"btn_toggle_reply_{comment_id}"):
                        toggle_reply_form(comment_id)

                # 展开回复表单
                if st.session_state.reply_forms.get(comment_id, False):
                    with st.container():
                        with st.form(key=f"reply_form_{comment_id}"):
                            reply_content = st.text_area("写下你的回复...", key=f"reply_input_{comment_id}")
                            submit_reply = st.form_submit_button("发送回复")

                            if submit_reply and reply_content.strip():
                                if not user_id:
                                    st.error("❌ 用户未登录，无法回复")
                                else:
                                    result = create_comment(
                                        user_id=user_id,
                                        content=reply_content,
                                        parent_id=comment_id,
                                        event_title=event_title
                                    )
                                    if result:
                                        st.success("✅ 回复成功！")
                                        st.rerun()
                                    else:
                                        st.error("❌ 提交回复失败，请重试")

                # 递归渲染子评论
                if comment["replies"]:
                    render_comment_tree(comment["replies"], depth + 1)

        render_comment_tree(root_comments)