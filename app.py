import json
from pathlib import Path
import streamlit as st

DATA_FILE = Path("todos.json")

def load_todos():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []

def save_todos(todos):
    DATA_FILE.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")

st.set_page_config(page_title="Todo 小工具", page_icon="✅", layout="centered")

st.title("✅ Todo 小工具（本地保存）")

# 读取数据
if "todos" not in st.session_state:
    st.session_state.todos = load_todos()

# 新增输入区
with st.form("add_form", clear_on_submit=True):
    new_text = st.text_input("新增待办：", placeholder="比如：交电费 / 背 20 个单词 / 写周报")
    submitted = st.form_submit_button("添加")
    if submitted:
        text = new_text.strip()
        if text:
            st.session_state.todos.append({"text": text, "done": False})
            save_todos(st.session_state.todos)
            st.success("已添加！")
        else:
            st.warning("请输入内容再添加。")

st.divider()

# 列表展示
st.subheader("📋 我的待办")
todos = st.session_state.todos

if not todos:
    st.info("还没有待办事项，先加一个吧～")
else:
    # 逐条显示：勾选完成 + 删除按钮
    for i, item in enumerate(todos):
        col1, col2, col3 = st.columns([0.1, 0.75, 0.15])

        with col1:
            checked = st.checkbox("", value=item["done"], key=f"done_{i}")

        with col2:
            if checked:
                st.markdown(f"~~{item['text']}~~")
            else:
                st.write(item["text"])

        with col3:
            if st.button("删除", key=f"del_{i}"):
                todos.pop(i)
                save_todos(todos)
                st.experimental_rerun()

        # 如果勾选状态改变，保存
        if checked != item["done"]:
            item["done"] = checked
            save_todos(todos)

st.divider()

# 一键清空已完成
if st.button("🧹 清空已完成"):
    st.session_state.todos = [t for t in st.session_state.todos if not t["done"]]
    save_todos(st.session_state.todos)
    st.success("已清空已完成事项！")
    st.experimental_rerun()

st.caption("数据保存在当前文件夹的 todos.json（不联网，仅本地）。")