"""Streamlit UI: employee chat + HRBP flag review.  Run:  streamlit run app.py"""
import os

import streamlit as st

from hr_bot import bot, llm, store

st.set_page_config(page_title="Kavach HR Policy Assistant", page_icon="🛡️")


@st.cache_resource
def load():
    store.load_policy()
    return store.load_roster()


try:
    ROSTER = load()
except store.DataError as e:
    st.error(f"Startup failed: {e}")
    st.stop()

page = st.sidebar.radio("View", ["Employee chat", "HRBP flag review"])
st.sidebar.caption(f"Intent fallback LLM: {'on (' + llm.MODEL + ')' if llm.enabled() else 'off — deterministic only'}")


def chat_page():
    st.title("🛡️ Kavach HR Policy Assistant")
    st.caption("Answers only from the Kavach HR Policy Pack v3.2 (fictional). Every message is logged for HRBP review.")
    ss = st.session_state
    if "bot" not in ss:
        ss.bot, ss.history = bot.Session(ROSTER), []

    with st.sidebar:
        st.subheader("Sign in")
        with st.form("login", clear_on_submit=True):
            eid = st.text_input("Employee ID", placeholder="e.g. KV1001")
            if st.form_submit_button("Start chat"):
                ss.bot, ss.history = bot.Session(ROSTER), []
                ss.history.append(("assistant", ss.bot.login(eid).text))
        if st.button("Continue without an ID"):
            ss.bot, ss.history = bot.Session(ROSTER), []
            ss.bot.as_guest()
            ss.history.append(("assistant", "OK — you're chatting without an Employee ID. I'll ask for details such "
                                            "as your band when an answer depends on them."))
        if ss.bot.profile and ss.bot.profile.employee_id:
            p = ss.bot.profile
            st.success(f"{p.name} · {p.employee_id}")
        st.caption(f"Session: {ss.bot.session_id}")

    if ss.bot.profile is None and not ss.history:
        st.info("Enter your Employee ID in the sidebar (or here in the chat) to begin.")
    for role, text in ss.history:
        st.chat_message(role).markdown(text)
    if msg := st.chat_input("Ask an HR policy question…"):
        st.chat_message("user").markdown(msg)
        try:
            reply = ss.bot.respond(msg)
            text = reply.text
        except Exception as e:  # never show a stack trace to an employee
            text = f"Sorry, something went wrong on my side ({type(e).__name__}). Please try again or contact HR at hr.help@kavach.example."
        ss.history += [("user", msg), ("assistant", text)]
        st.chat_message("assistant").markdown(text)


def hrbp_page():
    st.title("HRBP flag review")
    code = os.getenv("HRBP_VIEW_PASSCODE")
    if code and st.text_input("Passcode", type="password") != code:
        st.warning("Enter the HRBP passcode to view alerts.")
        st.stop()
    df = store.read_alerts()
    if df.empty:
        st.info("No alerts logged yet.")
        return
    c1, c2 = st.columns(2)
    hrbp = c1.selectbox("HRBP", ["All"] + sorted(x for x in df.hrbp_name.unique() if x) + ["(unverified employee)"])
    status = c2.selectbox("Status", ["open", "resolved", "All"])
    view = df
    if hrbp == "(unverified employee)":
        view = view[view.hrbp_name == ""]
    elif hrbp != "All":
        view = view[view.hrbp_name == hrbp]
    if status != "All":
        view = view[view.status == status]
    order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2}
    view = view.sort_values(["priority", "timestamp"], key=lambda s: s.map(order) if s.name == "priority" else s,
                            ascending=[True, False])
    st.metric("Alerts shown", len(view))
    st.dataframe(view, hide_index=True, width="stretch")
    open_ids = view[view.status == "open"].alert_id.tolist()
    if open_ids:
        aid = st.selectbox("Mark alert as resolved", open_ids)
        if st.button("Resolve"):
            store.set_alert_status(aid, "resolved")
            st.rerun()


if page == "Employee chat":
    chat_page()
else:
    hrbp_page()
