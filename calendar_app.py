import json
import time
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo

import streamlit as st
from streamlit_calendar import calendar  # pip install streamlit-calendar

# ✅ 把这里改成你真实所在时区
# 中国：Asia/Shanghai
# 美国洛杉矶：America/Los_Angeles
APP_TZ = "Asia/Shanghai"

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
    if isinstance(v, dict):
        if "todos" not in v or not isinstance(v.get("todos"), list):
            v["todos"] = []
        return v

    if isinstance(v, str):
        text = v.strip()
        if not text:
            return {"todos": []}
        lines = [line.strip().lstrip("-•").strip() for line in text.splitlines()]
        lines = [x for x in lines if x]
        return {"todos": [{"text": x, "done": False} for x in lines]}

    return {"todos": []}


def to_datestr_any(val):
    """把各种可能的日期返回值统一成 YYYY-MM-DD（按 APP_TZ）"""
    if val is None:
        return None

    if isinstance(val, str):
        # 'YYYY-MM-DD' 或 'YYYY-MM-DDT...' -> 先粗暴取前10位
        s = val[:10]
        # 兜底：如果是带 Z/偏移的时间字符串导致错一天，交给 datetime 解析
        # （有些版本会返回 '2026-02-19T16:00:00.000Z' 这种）
        if "T" in val:
            try:
                # Python 不能直接 parse 'Z'，替换成 +00:00
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return dt.astimezone(ZoneInfo(APP_TZ)).date().isoformat()
            except Exception:
                return s
        return s

    if isinstance(val, date) and not isinstance(val, datetime):
        return val.isoformat()

    if isinstance(val, datetime):
        if val.tzinfo is None:
            # 没 tz 的话，直接当作“本地日期”
            return val.date().isoformat()
        return val.astimezone(ZoneInfo(APP_TZ)).date().isoformat()

    return None


def extract_clicked_datestr(cal_state):
    """兼容不同 streamlit-calendar 版本回传结构"""
    if not isinstance(cal_state, dict):
        return None

    dc = cal_state.get("dateClick")
    if isinstance(dc, dict):
        # 优先 dateStr（通常最正确），没有再用 date
        return to_datestr_any(dc.get("dateStr")) or to_datestr_any(dc.get("date"))

    sel = cal_state.get("select")
    if isinstance(sel, dict):
        return to_datestr_any(sel.get("startStr")) or to_datestr_any(sel.get("start"))

    return to_datestr_any(cal_state.get("date")) or to_datestr_any(cal_state.get("start"))


st.set_page_config(page_title="共享日历", page_icon="📅", layout="wide")
st.title("📅 共享日历")

data = load_data()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today().isoformat()

# 黑点事件 + 自动迁移旧数据
events = []
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
        events.append({"title": "•", "start": str(k)[:10], "allDay": True})

if changed:
    save_data(data)

# ✅ 关键：把 FullCalendar 的时区写死成 APP_TZ（避免 UTC 导致少一天）
calendar_options = {
    "timeZone": APP_TZ,
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

    clicked_datestr = extract_clicked_datestr(cal_state)
    if clicked_datestr:
        st.session_state.selected_date = clicked_datestr

with right:
    selected = st.session_state.selected_date
    st.subheader(f"📝 {selected} 的事项")

    day = normalize_day_value(data.get(selected, {"todos": []}))
    data[selected] = day
    todos = day.get("todos", [])

    if not todos:
        st.info("当天还没有事项，下面添加一个吧。")

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
                data["_meta"] = {"last_saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_data(data)
                st.experimental_rerun()

        item["done"] = done
        item["text"] = text

    st.divider()

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