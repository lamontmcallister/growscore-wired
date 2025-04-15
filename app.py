
import streamlit as st

st.set_page_config(page_title="Skippr Debug", layout="wide")

# Print session state for visibility
st.title("🛠 Skippr Debug Mode")
st.write("This page will always render, even if the rest of the app fails.")

st.markdown("### Current session state:")
st.json(st.session_state)

if "page" not in st.session_state:
    st.session_state.page = "home"

if st.session_state.page == "home":
    st.markdown("## 👋 You're on the Homepage")
    if st.button("➡️ Go to App"):
        st.session_state.page = "app"

elif st.session_state.page == "app":
    st.markdown("## 🎯 App logic here")
    st.write("This is where the full Skippr platform would load.")
    if st.button("🔙 Go back"):
        st.session_state.page = "home"
