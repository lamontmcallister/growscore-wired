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

# --- CUSTOM CSS ---
def load_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
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
            .stSlider > div {
                padding-top: 0.5rem;
            }
            section[data-testid="stSidebar"] {
                background-color: #e6f0f8;
                border-right: 1px solid #cce0f5;
            }
            .markdown-block {
                background-color: #f8f8f8;
                padding: 1rem 1.5rem;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                margin-bottom: 1rem;
            }
        </style>
    """, unsafe_allow_html=True)


# --- SESSION STATE INIT ---
for k in ["supabase_session", "supabase_user", "step", "profiles", "active_profile", "active_profile_data"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "step" else 0

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

def delete_profile(profile_id):
    supabase.table("profiles").delete().eq("id", profile_id).execute()

# --- CANDIDATE PROFILE UI ---
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

        delete_choice = st.selectbox("Delete Profile", [p["profile_name"] for p in profiles])
        if st.button("Delete Selected Profile"):
            profile_id = next(p["id"] for p in profiles if p["profile_name"] == delete_choice)
            delete_profile(profile_id)
            st.success(f"Deleted profile: {delete_choice}")
            st.experimental_rerun()
    else:
        st.info("No profiles yet. Create your first one below!")

    st.markdown("---")
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

    st.progress((step + 1) / 10)

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
                skills = extract_skills_from_resume(resume_text)
                st.session_state.resume_skills = skills
                st.success("Resume parsed successfully!")

        if st.button("Next"):
            save_current_step_data({
                "name": name,
                "email": email,
                "title": title,
                "resume_text": st.session_state.get("resume_text", ""),
                "resume_skills": st.session_state.get("resume_skills", [])
            })
            next_step()

    # --- Step 1: Skills Selection ---
    elif step == 1:
        st.subheader("Step 2: Skills Selection")
        selected_skills = st.multiselect("Select Your Skills", SKILLS_POOL,
                                         default=st.session_state.active_profile_data.get("skills", st.session_state.get("resume_skills", [])))
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({"skills": selected_skills})
            next_step()

    # --- Step 2: Promotion & Tenure ---
    elif step == 2:
        st.subheader("Step 3: Career Progress")
        years_experience = st.slider("Years of Experience in Your Field", 0, 40,
                                     value=st.session_state.active_profile_data.get("years_experience", 2))
        num_promotions = st.slider("How Many Promotions Have You Received?", 0, 10,
                                   value=st.session_state.active_profile_data.get("num_promotions", 1))

        # Simple logic: Promotion velocity = promotions per year
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
    # --- Step 3: Behavioral Survey ---
    elif step == 3:
        st.subheader("Step 4: Behavioral Survey")
        behavior_questions = [
            "Meets deadlines consistently",
            "Collaborates well in teams",
            "Adapts quickly to change",
            "Demonstrates leadership",
            "Communicates effectively"
        ]
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        for i, question in enumerate(behavior_questions):
            response = st.radio(question, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (len(behavior_questions) * 5)) * 100, 1)
        st.session_state.behavior_score = behavior_score

        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({"behavior_score": behavior_score})
            next_step()

    # --- Step 4: References ---
    elif step == 4:
        st.subheader("Step 5: References")
        for i in range(1, 3):
            with st.expander(f"Reference {i}"):
                st.text_input("Name", key=f"ref{i}_name")
                st.text_input("Email", key=f"ref{i}_email")
                st.selectbox("Trait to Highlight", ["Leadership", "Communication", "Reliability"], key=f"ref{i}_trait")
                st.text_area("Optional Message", key=f"ref{i}_msg")
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            refs = {
                "references": [
                    {
                        "name": st.session_state.get(f"ref1_name", ""),
                        "email": st.session_state.get(f"ref1_email", ""),
                        "trait": st.session_state.get(f"ref1_trait", ""),
                        "msg": st.session_state.get(f"ref1_msg", "")
                    },
                    {
                        "name": st.session_state.get(f"ref2_name", ""),
                        "email": st.session_state.get(f"ref2_email", ""),
                        "trait": st.session_state.get(f"ref2_trait", ""),
                        "msg": st.session_state.get(f"ref2_msg", "")
                    }
                ],
                "ref_score": 85  # Placeholder for now
            }
            save_current_step_data(refs)
            next_step()

    # --- Step 5: Job Matching ---
    elif step == 5:
        st.subheader("Step 6: Job Matching")
        jd1 = st.text_area("Paste Job Description 1", value=st.session_state.active_profile_data.get("jd1", ""))
        jd2 = st.text_area("Paste Job Description 2", value=st.session_state.active_profile_data.get("jd2", ""))

        if st.button("Match Jobs"):
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            st.success(f"Match Scores: {scores}")
            save_current_step_data({"jd1": jd1, "jd2": jd2, "jd_scores": scores})

        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data()
            next_step()

    # --- Step 6: QoH Scoring ---
    elif step == 6:
        st.subheader("Step 7: Quality of Hire Score")
        jd_scores = st.session_state.active_profile_data.get("jd_scores", [75, 80])
        skill_count = len(st.session_state.active_profile_data.get("skills", []))
        behavior = st.session_state.active_profile_data.get("behavior_score", 50)
        ref_score = st.session_state.active_profile_data.get("ref_score", 85)
        promotion_velocity = st.session_state.active_profile_data.get("promotion_velocity", 0.5)
        years_experience = st.session_state.active_profile_data.get("years_experience", 2)

        # Composite QoH Calculation
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills_score = skill_count * 5
        tenure_score = min((years_experience / 10) * 100, 100)
        promotion_score = min(promotion_velocity * 100, 100)

        qoh = round((skills_score * 0.15 + ref_score * 0.15 + behavior * 0.15 +
                     avg_jd * 0.2 + promotion_score * 0.15 + tenure_score * 0.2) / 1, 1)

        st.metric("📈 Quality of Hire Score", f"{qoh}/100")
        st.progress(qoh / 100)

        save_current_step_data({
            "qoh": qoh,
            "skills_score": skills_score,
            "avg_jd": avg_jd,
            "promotion_score": promotion_score,
            "tenure_score": tenure_score
        })

        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            next_step()
    # --- Step 7: Growth Roadmap ---
    elif step == 7:
        st.subheader("Step 8: Growth Roadmap")
        prompt = f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\nCreate a career roadmap:\n• 30-day\n• 60-day\n• 90-day\n• 6-month\n• 1-year"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Onboard\n• 60-Day: Deliver small win\n• 90-Day: Lead initiative\n• 6-Month: Strategic growth\n• 1-Year: Prepare for promotion"

        st.text_area("Growth Roadmap", roadmap, height=250)
        save_current_step_data({"roadmap": roadmap})

        if st.button("Back"):
            prev_step()
        if st.button("Finish"):
            st.success("🎉 Profile complete and saved!")
            st.balloons()
            st.write("You can revisit this profile anytime to continue improving your Quality of Hire score.")

# --- End of Journey ---
else:
    st.markdown("### 👤 Select or Create a Profile to Begin")
    profile_selector_ui()
# --- Recruiter Dashboard ---
st.markdown("---")
st.header("💼 Recruiter Dashboard")

# Fetch all candidate profiles
user_id = st.session_state.supabase_user.id
profiles = get_profiles(user_id)

if profiles:
    st.subheader("📊 Candidate Overview")

    df_data = []
    for profile in profiles:
        data = profile["data"]
        df_data.append({
            "Candidate": data.get("name", ""),
            "QoH Score": data.get("qoh", 0),
            "Skills Count": len(data.get("skills", [])),
            "JD Match": data.get("avg_jd", 0),
            "Promotion Score": data.get("promotion_score", 0),
            "Tenure Score": data.get("tenure_score", 0),
            "Behavior": data.get("behavior_score", 0),
            "References": data.get("ref_score", 0),
            "Profile Name": profile.get("profile_name", "")
        })

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)

    # Sort candidates by QoH Score
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
