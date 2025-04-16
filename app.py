# Skippr App – Full Candidate Journey with Dropdowns and Sidebar Login
# Final MVP wiring: sidebar login, candidate journey dropdowns, toggle view

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Skippr", layout="wide")

# Session state
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = True  # Simulate logged in
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Candidate"

# Toggle view top-right
st.markdown("<div style='position: fixed; top: 10px; right: 20px;'>", unsafe_allow_html=True)
mode = st.radio("View Mode", ["Candidate", "Recruiter"], horizontal=True, key="mode_toggle")
st.session_state.view_mode = mode
st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.view_mode == "Candidate":
    st.title("🎯 Candidate Journey")

    with st.expander("📄 Step 1: Upload Resume"):
        st.file_uploader("Upload your resume (PDF)", type=["pdf"])
        st.markdown("_We’ll extract skills and experience automatically._")

    with st.expander("🎓 Step 2: Add Education"):
        st.text_input("School Name")
        st.text_input("Degree")
        st.text_input("Field of Study")
        st.text_input("Graduation Year")

    with st.expander("🤝 Step 3: Add References"):
        ref1 = st.text_input("Reference 1 Name")
        ref1_email = st.text_input("Reference 1 Email")
        st.button("Send Request", key="send_ref_1")

        ref2 = st.text_input("Reference 2 Name")
        ref2_email = st.text_input("Reference 2 Email")
        st.button("Send Request", key="send_ref_2")

    with st.expander("📝 Step 4: Match to Job Descriptions"):
        jd1 = st.text_area("Paste Job Description 1")
        jd2 = st.text_area("Paste Job Description 2")
        st.button("Analyze Match")
        st.markdown("_Match visualization and radar chart coming soon._")

    with st.expander("📈 Final Step: Review Your Score"):
        st.metric("Quality of Hire", "82", delta="+9")
        st.success("🎉 Profile complete! You’re ready to share with recruiters.")
else:
    st.title("📊 Recruiter Dashboard (Coming Soon)")
    st.info("This view will show candidate comparison cards, scoring sliders, and AI suggestions.")
