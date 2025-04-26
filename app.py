import streamlit as st
import openai
import pdfplumber
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import datetime
import ast

# --- CONFIG ---
st.set_page_config(page_title="Skippr | Candidate Growth Intelligence", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- TEMP USER MOCK ---
if "supabase_user" not in st.session_state or st.session_state.supabase_user is None:
    st.session_state.supabase_user = type("User", (), {"id": "test-user-1234"})

# --- CUSTOM CSS ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
                padding: 0rem !important;
                background-color: #f5f7fa;
            }
            h1, h2, h3 {
                font-weight: 600 !important;
                margin-bottom: 0.5rem;
                color: #003366;
            }
            div.stButton > button {
                background-color: #0072ce;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0.5rem 1.2rem;
                font-weight: 600;
                font-size: 1rem;
                margin-top: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- PROFILE MANAGEMENT ---
def get_profiles(user_id):
    res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    return res.data if res.data else []

def save_profile(user_id, profile_name, data):
    existing = supabase.table("profiles").select("id").eq("user_id", user_id).eq("profile_name", profile_name).execute()
    if existing.data:
        profile_id = existing.data[0]["id"]
        supabase.table("profiles").update({"data": data}).eq("id", profile_id).execute()
    else:
        supabase.table("profiles").insert({"user_id": user_id, "profile_name": profile_name, "data": data}).execute()

# --- MULTI-PROFILE UI ---
def profile_selector_ui():
    st.markdown("### 👤 Manage Your Profiles")
    user_id = st.session_state.supabase_user.id
    profiles = get_profiles(user_id)

    if profiles:
        selected_profile = st.selectbox("Select Existing Profile", [p["profile_name"] for p in profiles])
        if st.button("Load Profile"):
            profile_data = next(p["data"] for p in profiles if p["profile_name"] == selected_profile)
            st.session_state.active_profile = selected_profile
            st.session_state.active_profile_data = profile_data
            st.session_state.step = profile_data.get("step", 0)
            st.success(f"Loaded profile: {selected_profile}")
            st.experimental_rerun()

    new_profile_name = st.text_input("New Profile Name")
    if new_profile_name and st.button("Start New Profile"):
        st.session_state.profile_name = new_profile_name
        st.session_state.active_profile_data = {}
        st.session_state.step = 0
        save_profile(user_id, new_profile_name, {"step": 0})
        st.success(f"Profile '{new_profile_name}' created!")
        st.experimental_rerun()
# --- Candidate Journey ---
if "profile_name" in st.session_state:
    st.header(f"🚀 Journey: {st.session_state.profile_name}")
    step = st.session_state.get("step", 0)

    def save_current_step_data(extra_data={}):
        user_id = st.session_state.supabase_user.id
        profile_data = st.session_state.active_profile_data or {}
        profile_data.update(extra_data)
        profile_data["step"] = step
        save_profile(user_id, st.session_state.profile_name, profile_data)
        st.session_state.active_profile_data = profile_data

    def next_step():
        st.session_state.step += 1
        save_current_step_data()

    def prev_step():
        st.session_state.step = max(0, st.session_state.step - 1)
        save_current_step_data()

    st.progress((step + 1) / 8)

    # --- Step 0: Contact Info + Resume Upload ---
    if step == 0:
        st.subheader("Step 1: Contact Info + Resume Upload")
        name = st.text_input("Full Name", value=st.session_state.active_profile_data.get("name", ""))
        email = st.text_input("Email", value=st.session_state.active_profile_data.get("email", ""))
        title = st.text_input("Target Job Title", value=st.session_state.active_profile_data.get("title", ""))
        uploaded = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

        if uploaded:
            with pdfplumber.open(uploaded) as pdf:
                resume_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                st.session_state.resume_text = resume_text
                st.success("Resume parsed successfully!")

        if st.button("Next"):
            save_current_step_data({
                "name": name,
                "email": email,
                "title": title,
                "resume_text": st.session_state.get("resume_text", "")
            })
            next_step()

    # --- Step 1: Skills Selection ---
    elif step == 1:
        st.subheader("Step 2: Skills Selection")
        SKILLS_POOL = ["Python", "SQL", "Leadership", "Machine Learning", "Communication", "Excel"]
        selected_skills = st.multiselect("Select Your Skills", SKILLS_POOL,
                                         default=st.session_state.active_profile_data.get("skills", []))
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({"skills": selected_skills})
            next_step()

    # --- Step 2: Promotion & Tenure ---
    elif step == 2:
        st.subheader("Step 3: Career Progress")
        years_experience = st.slider("Years of Experience", 0, 40,
                                     value=st.session_state.active_profile_data.get("years_experience", 2))
        num_promotions = st.slider("Number of Promotions", 0, 10,
                                   value=st.session_state.active_profile_data.get("num_promotions", 1))

        promotion_velocity = round(num_promotions / max(years_experience, 1), 2)
        st.metric("Promotion Velocity", f"{promotion_velocity} per year")

        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({
                "years_experience": years_experience,
                "num_promotions": num_promotions,
                "promotion_velocity": promotion_velocity
            })
            next_step()
    # --- Step 3: QoH Scoring ---
    elif step == 3:
        st.subheader("Step 4: Quality of Hire Score")
        skill_count = len(st.session_state.active_profile_data.get("skills", []))
        behavior = st.session_state.active_profile_data.get("behavior_score", 70)  # Placeholder if missing
        ref_score = 85  # Placeholder for now
        promotion_velocity = st.session_state.active_profile_data.get("promotion_velocity", 0.5)
        years_experience = st.session_state.active_profile_data.get("years_experience", 2)
        jd_score = 80  # Placeholder JD match %

        # Derived Scores
        skills_score = skill_count * 5
        tenure_score = min((years_experience / 10) * 100, 100)
        promotion_score = min(promotion_velocity * 100, 100)

        qoh = round((skills_score * 0.15 + ref_score * 0.15 + behavior * 0.15 +
                     jd_score * 0.2 + promotion_score * 0.15 + tenure_score * 0.2), 1)

        st.metric("📈 Quality of Hire Score", f"{qoh}/100")
        st.progress(qoh / 100)

        save_current_step_data({
            "qoh": qoh,
            "skills_score": skills_score,
            "jd_score": jd_score,
            "promotion_score": promotion_score,
            "tenure_score": tenure_score
        })

        if st.button("Back"):
            prev_step()
        if st.button("Finish"):
            st.success("🎉 Profile complete and saved!")
            st.balloons()

# --- Recruiter Dashboard ---
st.markdown("---")
st.header("💼 Recruiter Dashboard")

profiles = get_profiles(st.session_state.supabase_user.id)

if profiles:
    st.subheader("📊 Candidate Overview")

    df_data = []
    for profile in profiles:
        data = profile["data"]
        df_data.append({
            "Candidate": data.get("name", ""),
            "QoH Score": data.get("qoh", 0),
            "Skills Count": len(data.get("skills", [])),
            "JD Match": data.get("jd_score", 0),
            "Promotion Score": data.get("promotion_score", 0),
            "Tenure Score": data.get("tenure_score", 0),
            "Behavior": data.get("behavior_score", 0),
            "References": data.get("ref_score", 85),
            "Profile Name": profile.get("profile_name", "")
        })

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)

    sorted_df = df.sort_values(by="QoH Score", ascending=False)

    st.subheader("🏆 Top Candidates")
    for _, row in sorted_df.iterrows():
        if row["QoH Score"] >= 85:
            st.success(f"{row['Candidate']} ({row['Profile Name']}) - QoH: {row['QoH Score']}")
        elif row["References"] < 70:
            st.warning(f"{row['Candidate']} - Low reference strength.")
        elif row["Promotion Score"] < 50:
            st.info(f"{row['Candidate']} - Limited career progression.")
        else:
            st.write(f"{row['Candidate']} - Solid candidate. QoH: {row['QoH Score']}")

else:
    st.info("No candidate profiles available yet.")
