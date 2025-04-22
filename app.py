import streamlit as st
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- STYLE ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] {
                font-family: 'Segoe UI', sans-serif;
                padding: 0rem !important;
            }
            h1, h2, h3 {
                font-weight: 600 !important;
                margin-bottom: 0.5rem;
            }
            div.stButton > button {
                background-color: #ff6a00;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0.5rem 1.2rem;
                font-weight: 600;
                font-size: 1rem;
                margin-top: 0.5rem;
            }
            section[data-testid="stSidebar"] {
                background-color: #f9f4ef;
                border-right: 1px solid #e1dfdb;
            }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION INIT ---
for k in ["supabase_session", "supabase_user", "step", "selected_profile_id"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "step" else 0

# --- GPT UTILS ---
def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\n{text}\nReturn as a Python list."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0.3
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return ["Python", "SQL", "Excel"]

def extract_contact_info(text):
    prompt = f"From this resume, extract the full name, email, and job title. Return a Python dictionary with keys: name, email, title.\n\n{text}"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0.2
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return {"name": "", "email": "", "title": ""}

def match_resume_to_jds(resume_text, jd_texts):
    prompt = f"Given this resume:\n{resume_text}\n\nMatch semantically to the following JDs:\n"
    for i, jd in enumerate(jd_texts):
        prompt += f"\nJD {i+1}:\n{jd}\n"
    prompt += "\nReturn a list of match scores, e.g. [82, 76]"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0.2,
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return [np.random.randint(70, 90) for _ in jd_texts]

# --- PROFILE LOGIC ---
def save_profile(profile_id=None):
    data = {
        "name": st.session_state.get("cand_name", ""),
        "email": st.session_state.get("cand_email", ""),
        "title": st.session_state.get("cand_title", ""),
        "skills": st.session_state.get("selected_skills", []),
        "behavior_score": st.session_state.get("behavior_score", 0),
        "jd_scores": st.session_state.get("jd_scores", []),
        "qoh_score": st.session_state.get("qoh_score", 0),
        "references": {
            "ref1": {
                "name": st.session_state.get("ref1_name", ""),
                "email": st.session_state.get("ref1_email", ""),
                "trait": st.session_state.get("ref1_trait", ""),
                "msg": st.session_state.get("ref1_msg", "")
            },
            "ref2": {
                "name": st.session_state.get("ref2_name", ""),
                "email": st.session_state.get("ref2_email", ""),
                "trait": st.session_state.get("ref2_trait", ""),
                "msg": st.session_state.get("ref2_msg", "")
            }
        }
    }

    if profile_id:
        supabase.table("profiles").update(data).eq("id", profile_id).execute()
    else:
        supabase.table("profiles").insert({**data, "user_id": st.session_state.supabase_user["id"]}).execute()

def load_profile(profile_id):
    res = supabase.table("profiles").select("*").eq("id", profile_id).single().execute()
    profile = res.data
    if profile:
        st.session_state["cand_name"] = profile.get("name", "")
        st.session_state["cand_email"] = profile.get("email", "")
        st.session_state["cand_title"] = profile.get("title", "")
        st.session_state["selected_skills"] = profile.get("skills", [])
        st.session_state["behavior_score"] = profile.get("behavior_score", 0)
        st.session_state["jd_scores"] = profile.get("jd_scores", [])
        st.session_state["qoh_score"] = profile.get("qoh_score", 0)
        refs = profile.get("references", {})
        st.session_state["ref1_name"] = refs.get("ref1", {}).get("name", "")
        st.session_state["ref1_email"] = refs.get("ref1", {}).get("email", "")
        st.session_state["ref1_trait"] = refs.get("ref1", {}).get("trait", "")
        st.session_state["ref1_msg"] = refs.get("ref1", {}).get("msg", "")
        st.session_state["ref2_name"] = refs.get("ref2", {}).get("name", "")
        st.session_state["ref2_email"] = refs.get("ref2", {}).get("email", "")
        st.session_state["ref2_trait"] = refs.get("ref2", {}).get("trait", "")
        st.session_state["ref2_msg"] = refs.get("ref2", {}).get("msg", "")

def profile_selector():
    if not st.session_state.supabase_user:
        return
    user_id = st.session_state.supabase_user["id"]
    res = supabase.table("profiles").select("id, name").eq("user_id", user_id).execute()
    profiles = res.data or []
    if not profiles:
        new = st.text_input("🔐 Create new profile name to start")
        if new and st.button("Create"):
            new_id = supabase.table("profiles").insert({"user_id": user_id, "name": new}).execute().data[0]["id"]
            st.session_state.selected_profile_id = new_id
            st.experimental_rerun()
    else:
        choice = st.selectbox("Choose profile", [p["name"] for p in profiles] + ["➕ Create New"])
        if choice == "➕ Create New":
            new = st.text_input("New profile name")
            if new and st.button("Create"):
                new_id = supabase.table("profiles").insert({"user_id": user_id, "name": new}).execute().data[0]["id"]
                st.session_state.selected_profile_id = new_id
                st.experimental_rerun()
        else:
            selected = next((p for p in profiles if p["name"] == choice), None)
            if selected:
                st.session_state.selected_profile_id = selected["id"]
                load_profile(selected["id"])
# --- CANDIDATE JOURNEY ---
def candidate_journey():
    if not st.session_state.get("selected_profile_id"):
        profile_selector()
        return

    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    skills_pool = [
        "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
        "Communication", "Strategic Planning", "Excel", "Project Management"
    ]
    traits = [
        "Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork",
        "Adaptability", "Problem Solving", "Empathy", "Initiative", "Collaboration"
    ]

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state["resume_contact"] = extract_contact_info(text)
            st.success("Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.multiselect("Your Skills", skills_pool, default=st.session_state.get("resume_skills", []), key="selected_skills")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        total = 0
        questions = [
            "Meets deadlines", "Works well in teams", "Adapts to change",
            "Shows leadership", "Communicates clearly"
        ]
        for i, q in enumerate(questions):
            resp = st.radio(q, opts, index=2, key=f"behavior_{i}")
            total += score_map[resp]
        st.session_state.behavior_score = round((total / (len(questions) * 5)) * 100, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        with st.expander("Reference 1"):
            st.text_input("Name", key="ref1_name")
            st.text_input("Email", key="ref1_email")
            st.selectbox("Trait", traits, key="ref1_trait")
            st.text_area("Message", key="ref1_msg")
        with st.expander("Reference 2"):
            st.text_input("Name", key="ref2_name")
            st.text_input("Email", key="ref2_email")
            st.selectbox("Trait", traits, key="ref2_trait")
            st.text_area("Message", key="ref2_msg")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.text_input("Backchannel Name")
        st.text_input("Backchannel Email")
        st.text_area("Feedback Request")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("School")
        st.text_input("Grad Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.text_input("Most Recent Company")
        st.text_input("Manager Name")
        st.text_input("HR Contact Email")
        st.checkbox("Authorize Verification")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        jd1 = st.text_area("Paste JD 1")
        jd2 = st.text_area("Paste JD 2")
        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1}:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        jd = st.session_state.get("jd_scores", [80, 85])
        skills = len(st.session_state.get("selected_skills", [])) * 5
        avg = round(sum(jd) / len(jd), 1)
        ref = 90
        beh = st.session_state.get("behavior_score", 50)
        qoh = round((skills + ref + beh + avg) / 4, 1)
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        prompt = f"Resume:\n{st.session_state.get('resume_text', '')}\n\nGive a roadmap:\n- 30/60/90 days\n- 6mo\n- 1yr"
        try:
            roadmap = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0.6
            ).choices[0].message.content.strip()
        except:
            roadmap = "30: onboard\n60: own project\n90: deliver\n6mo: lead\n1yr: promote"
        st.markdown("### Growth Roadmap")
        st.markdown(roadmap)
        save_profile(st.session_state.selected_profile_id)
        st.success("🎉 Profile saved!")

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")

    default_weights = {"JD Match": 25, "References": 25, "Behavior": 25, "Skills": 25}
    custom_criteria = st.text_input("➕ Add Custom QoH Field")
    if custom_criteria:
        if "custom_qoh" not in st.session_state:
            st.session_state.custom_qoh = {}
        if custom_criteria not in st.session_state.custom_qoh:
            st.session_state.custom_qoh[custom_criteria] = 10
            st.success(f"Added {custom_criteria}")

    all_weights = default_weights.copy()
    if "custom_qoh" in st.session_state:
        all_weights.update(st.session_state.custom_qoh)

    updated = {}
    for k in all_weights:
        updated[k] = st.slider(k, 0, 100, all_weights[k])
    total = sum(updated.values())
    if total == 0: return st.warning("Assign weights!")

    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "References": 90, "Behavior": 84, "Skills": 92, "Strategic Thinking": 70},
        {"Candidate": "Jasmine", "JD Match": 82, "References": 78, "Behavior": 90, "Skills": 80, "Strategic Thinking": 85},
        {"Candidate": "Andre", "JD Match": 75, "References": 65, "Behavior": 70, "Skills": 78, "Strategic Thinking": 60}
    ])

    def qoh(row): return round(sum(row.get(k, 0) * updated[k] for k in updated) / total, 2)
    df["QoH"] = df.apply(qoh, axis=1)
    st.dataframe(df[["Candidate"] + list(updated.keys()) + ["QoH"]])

# --- LOGIN UI ---
def login_ui():
    st.markdown("### From Rejection to Revolution")
    with st.sidebar:
        st.header("🔐 Login or Sign Up")
        mode = st.radio("Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.supabase_user = res.user
                st.success("Logged in")
                st.rerun()
            except Exception as e:
                st.error("Login failed")
        if mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": pwd})
                st.success("Check email to confirm.")
            except:
                st.error("Signup error")

# --- ROUTING ---
if st.session_state.supabase_user:
    view = st.sidebar.radio("View", ["Candidate", "Recruiter"])
    if view == "Candidate":
        candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
