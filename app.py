
import streamlit as st
from PIL import Image
import pandas as pd

st.set_page_config(page_title="Skippr", layout="wide")

# Session state defaults
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None
if "show_app" not in st.session_state:
    st.session_state.show_app = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Candidate"

# ---------- LOGIN SIDEBAR ----------
with st.sidebar:
    st.image("https://i.ibb.co/tPDqFQF/skippr-logo-dark.png", width=120)
    st.header("👤 Candidate Login")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"], key="auth_mode")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("🔐 Login"):
        st.session_state.supabase_user = {"email": email}
        st.session_state.show_app = True
    if st.button("New here? Create account"):
        st.success("Feature coming soon.")

# ---------- LOGIN PAGE IMAGE ----------
if not st.session_state.show_app:
    st.markdown(
        "<div style='text-align: center; padding-top: 2rem;'>"
        "<img src='https://images.unsplash.com/photo-1600195077073-3c9b46be6405?auto=format&fit=crop&w=1450&q=80' width='75%'>"
        "<p style='color: gray; margin-top: 10px;'>Helping you skip the noise and land faster.</p>"
        "</div>",
        unsafe_allow_html=True
    )
    st.stop()

# ---------- APP VIEW TOGGLE ----------
st.markdown("<div style='position: fixed; top: 10px; right: 20px;'>", unsafe_allow_html=True)
mode = st.radio("Mode", ["Candidate", "Recruiter"], horizontal=True, key="mode_toggle")
st.session_state.view_mode = mode
st.markdown("</div>", unsafe_allow_html=True)

# ---------- CANDIDATE JOURNEY ----------
def show_candidate_journey():
    st.title("🎯 Candidate Journey")
    with st.expander("📄 Step 1: Upload Resume"):
        st.file_uploader("Upload your resume (PDF)", type=["pdf"])

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
        st.markdown("_Radar chart and semantic match scoring coming soon._")

    with st.expander("📈 Final Step: Review Your Score"):
        st.metric("Quality of Hire", "82", delta="+9")
        st.success("🎉 Profile complete! You’re ready to share with recruiters.")

# ---------- RECRUITER DASHBOARD ----------
def show_recruiter_dashboard():
    st.title("📊 Recruiter Dashboard")
    st.dataframe(pd.DataFrame({
        "Candidate": ["Jordan", "Alex", "Taylor"],
        "QoH Score": [82, 76, 90],
        "Match %": [88, 80, 95],
        "Reference Score": [5, 4, 5]
    }))
    st.slider("Resume Match", 0, 100, 40)
    st.slider("References", 0, 100, 30)
    st.slider("Education", 0, 100, 30)
    st.success("Jordan ranks highest overall. Recommend for next round.")

# ---------- VIEW ROUTING ----------
if st.session_state.view_mode == "Candidate":
    show_candidate_journey()
else:
    show_recruiter_dashboard()
