import json
import time
from pathlib import Path
from datetime import date

import streamlit as st
from streamlit_calendar import calendar  # pip install streamlit-calendar

DATA_FILE = Path("calendar.json")


def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_day_value(v):
    """
    兼容旧数据：
    - 旧：v 是 str（当天一段文本）
    - 新：v 是 dict，形如 {"todos":[{"text":..., "done":...}, ...]}
    统一返回 dict
    """
    if isinstance(v, dict):
        if "todos" not in v or not isinstance(v.get("todos"), list):
            v["todos"] = []
        return v

    if isinstance(v, str):
        text = v.strip()
        if not text:
            return {"todos": []}
        # 把旧文本按行拆成 todo（支持 - / • 开头）
        lines = [line.strip().lstrip("-•").strip() for line in text.splitlines()]
        lines = [x for x in lines if x]
        return {"todos": [{"text": x, "done": False} for x in lines]}

    return {"todos": []}


st.set_page_config(page_title="共享日历", page_icon="📅", layout="wide")
st.title("📅 共享日历（大月历 + 黑点）")

data = load_data()

# --- 状态：当前选中的日期 ---
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today().isoformat()

# --- 生成事件（黑点）+ 自动迁移旧数据 ---
events = []  # ✅ 一定要在循环前定义
changed = False

for k, v in list(data.items()):
    if str(k).startswith("_"):
        continue

    day = normalize_day_value(v)
    if day is not v:
        data[k] = day
        changed = True

    todos = day.get("todos", [])
    if any(str(t.get("text", "")).strip() for t in todos):
        events.append({"title": "•", "start": str(k), "allDay": True})

if changed:
    save_data(data)

# --- 日历配置 ---
calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,dayGridWeek",
    },
    "selectable": True,
    "editable": False,
    "dayMaxEvents": True,
    "height": 720,
}

custom_css = """
.fc .fc-daygrid-event {
  border: none !important;
  background: transparent !important;
}
.fc .fc-daygrid-event .fc-event-title {
  font-size: 18px;
  color: #111 !important;
  font-weight: 900;
}
"""

left, right = st.columns([2.2, 1.2], gap="large")

with left:
    st.subheader("🗓️ 月历")
    cal_state = calendar(
        events=events,
        options=calendar_options,
        custom_css=custom_css,
        key="calendar",
    )

    clicked_date = None
    if isinstance(cal_state, dict):
        if isinstance(cal_state.get("dateClick"), dict):
            clicked_date = cal_state["dateClick"].get("date")
        if not clicked_date and isinstance(cal_state.get("select"), dict):
            clicked_date = cal_state["select"].get("start")

    if clicked_date:
        st.session_state.selected_date = str(clicked_date)[:10]  # 兼容带时间的格式

with right:
    selected = st.session_state.selected_date
    st.subheader(f"📝 {selected} 的事项")

    day = normalize_day_value(data.get(selected, {"todos": []}))
    data[selected] = day  # 确保写回是新结构
    todos = day.get("todos", [])

    if not todos:
        st.info("当天还没有事项，下面添加一个吧。")

    # 展示/编辑当天 todos
    for idx, item in enumerate(list(todos)):
        c1, c2, c3 = st.columns([0.15, 0.70, 0.15])

        done_key = f"done_{selected}_{idx}"
        text_key = f"text_{selected}_{idx}"
        del_key = f"del_{selected}_{idx}"

        with c1:
            done = st.checkbox("", value=bool(item.get("done", False)), key=done_key)
        with c2:
            text = st.text_input(
                "事项",
                value=str(item.get("text", "")),
                label_visibility="collapsed",
                key=text_key,
            )
        with c3:
            if st.button("删除", key=del_key):
                todos.pop(idx)
                day["todos"] = todos
                data[selected] = day
                data["_meta"] = {
                    "last_saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                save_data(data)
                st.experimental_rerun()

        item["done"] = done
        item["text"] = text

    st.divider()

    # 添加
    new = st.text_input("新增事项", placeholder="例如：买菜 / 约医生 / 交水电费", key=f"new_{selected}")
    colA, colB = st.columns([1, 1])

    with colA:
        if st.button("➕ 添加", key=f"add_{selected}"):
            t = new.strip()
            if t:
                todos.append({"text": t, "done": False})
                day["todos"] = todos
                data[selected] = day
                save_data(data)
                st.experimental_rerun()
            else:
                st.warning("请输入内容再添加。")

    with colB:
        if st.button("💾 保存当天", key=f"save_{selected}"):
            cleaned = [
                {"text": str(t.get("text", "")).strip(), "done": bool(t.get("done", False))}
                for t in todos
                if str(t.get("text", "")).strip()
            ]
            day["todos"] = cleaned
            data[selected] = day
            data["_meta"] = {"last_saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            save_data(data)
            st.success("已保存！黑点会在刷新/切换月份后出现。")

st.caption("同步建议：把整个项目文件夹放进 OneDrive/Dropbox 同步目录，你和你老婆各自运行，就能共享同一份 calendar.json。")