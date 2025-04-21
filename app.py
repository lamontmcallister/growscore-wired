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

# --- CSS ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] {
                font-family: 'Segoe UI', sans-serif;
                padding: 0rem !important;
            }
            div.stButton > button {
                background-color: #ff6a00;
                color: white;
                border-radius: 6px;
                padding: 0.5rem 1.2rem;
                font-weight: 600;
                font-size: 1rem;
                margin-top: 0.5rem;
                border: none;
            }
        </style>
    """, unsafe_allow_html=True)
load_custom_css()

# --- SESSION SETUP ---
for k in ["supabase_user", "supabase_session", "step", "active_profile_id"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "step" else 0

skills_pool = [
    "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
    "Communication", "Strategic Planning", "Excel", "Project Management"
]

# --- GPT HELPERS ---
def extract_skills_from_resume(text):
    prompt = f"Extract 5–10 professional skills from this resume:\n{text}\nReturn as a Python list."
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return ["Python", "SQL", "Excel"]

def extract_contact_info(text):
    prompt = f"From this resume, extract the full name, email, and job title. Return a Python dictionary with keys: name, email, title.\n\n{text}"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
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
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return ast.literal_eval(res.choices[0].message.content.strip())
    except:
        return [np.random.randint(70, 90) for _ in jd_texts]

# --- PROFILE HELPERS ---
def load_profiles():
    user_id = st.session_state.supabase_user.id
    res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    return res.data if res.data else []

def save_profile(profile_data):
    profile_data["user_id"] = st.session_state.supabase_user.id
    profile_data["timestamp"] = datetime.utcnow().isoformat()
    supabase.table("profiles").insert(profile_data).execute()

def profile_selector():
    profiles = load_profiles()
    profile_names = [p["name"] for p in profiles]
    if not profiles:
        st.session_state.active_profile_id = None
        st.warning("No profiles found. Please create one to begin.")
        name = st.text_input("Enter profile name:")
        if st.button("Create Profile") and name:
            new_profile = {"name": name}
            res = supabase.table("profiles").insert({**new_profile, "user_id": st.session_state.supabase_user.id}).execute()
            st.rerun()
    else:
        choice = st.selectbox("Choose a profile to continue:", profile_names)
        st.session_state.active_profile_id = next((p["id"] for p in profiles if p["name"] == choice), None)
# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Contact Info")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.session_state["resume_contact"] = extract_contact_info(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        selected = st.multiselect("Choose your strongest skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.caption("Tell us how you show up at work. Choose the statement that best reflects you for each trait.")
        behavior_questions = {
            "Meets deadlines consistently": None,
            "Collaborates well in teams": None,
            "Adapts quickly to change": None,
            "Demonstrates leadership": None,
            "Communicates effectively": None,
        }
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        for i, question in enumerate(behavior_questions):
            response = st.radio(question, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (len(behavior_questions) * 5)) * 100, 1)
        st.session_state.behavior_score = behavior_score
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        traits = [
            "Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork",
            "Adaptability", "Problem Solving", "Empathy", "Initiative", "Collaboration"
        ]
        with st.expander("Reference 1 Details"):
            st.text_input("Name", key="ref1_name")
            st.text_input("Email", key="ref1_email")
            st.selectbox("Trait to Highlight", traits, key="ref1_trait")
            st.text_area("Message to Referee (optional)", key="ref1_msg")
            if st.button("Send Request to Ref 1"):
                st.success(f"Request sent to {st.session_state.get('ref1_name')}")

        with st.expander("Reference 2 Details"):
            st.text_input("Name", key="ref2_name")
            st.text_input("Email", key="ref2_email")
            st.selectbox("Trait to Highlight", traits, key="ref2_trait")
            st.text_area("Message to Referee (optional)", key="ref2_msg")
            if st.button("Send Request to Ref 2"):
                st.success(f"Request sent to {st.session_state.get('ref2_name')}")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Backchannel Check (Optional)")
        st.text_input("Backchannel Contact Name")
        st.text_input("Backchannel Email")
        st.text_area("Message or Topic for Feedback")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education Background")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Graduation Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 🏢 Step 7: HR Verification")
        st.text_input("Most Recent Company")
        st.text_input("Manager's Name")
        st.text_input("HR Contact Email")
        st.checkbox("I authorize verification with these contacts")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: JD Matching & Skills Gap")
        jd1 = st.text_area("Paste Job Description 1", height=150)
        jd2 = st.text_area("Paste Job Description 2", height=150)

        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            st.success("✅ JD Matching Complete")

            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")

            candidate_skills = set(st.session_state.get("selected_skills", []))
            jd_skills = [
                set([word for word in jd1.split() if word.istitle()]),
                set([word for word in jd2.split() if word.istitle()])
            ]

            st.markdown("### 🧩 Skills Gap")
            for i, jd_set in enumerate(jd_skills):
                gaps = list(jd_set - candidate_skills)
                st.markdown(f"**JD {i+1} Gaps:**")
                if gaps:
                    st.warning(", ".join(gaps))
                else:
                    st.success("You're well aligned with this JD!")

        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire Summary")
        jd_scores = st.session_state.get("jd_scores", [70, 80])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        ref_score = 90
        behavior = st.session_state.get("behavior_score", 50)
        qoh = round((skills + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("📈 Quality of Hire (QoH)", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Career Growth Roadmap")
        prompt = f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\nGenerate a growth roadmap for this candidate:\n- 30-day\n- 60-day\n- 90-day\n- 6-month\n- 1-year career trajectory"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Learn onboarding systems\n• 60-Day: Deliver project win\n• 90-Day: Lead a team initiative\n• 6-Month: Improve cross-functional impact\n• 1-Year: Prepare for leadership."
        st.markdown(f"**Your Growth Roadmap:**\n\n{roadmap}")
        st.success("🎉 Candidate Journey Complete!")

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚 Adjust Quality of Hire Weights", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Adjust sliders to see candidate scores.")
        return

    df = pd.DataFrame([
        {
            "Candidate": "Lamont",
            "JD Match": 88,
            "Reference": 90,
            "Behavior": 84,
            "Skill": 92,
            "Gaps": "Strategic Planning",
            "Verified": "✅ Resume, ✅ References, ✅ JD, 🟠 Behavior, ✅ Education, ✅ HR"
        },
        {
            "Candidate": "Jasmine",
            "JD Match": 82,
            "Reference": 78,
            "Behavior": 90,
            "Skill": 80,
            "Gaps": "Leadership",
            "Verified": "✅ Resume, ⚠️ References, ✅ JD, ✅ Behavior, ✅ Education, ❌ HR"
        },
        {
            "Candidate": "Andre",
            "JD Match": 75,
            "Reference": 65,
            "Behavior": 70,
            "Skill": 78,
            "Gaps": "Communication",
            "Verified": "✅ Resume, ❌ References, ✅ JD, ⚠️ Behavior, ❌ Education, ❌ HR"
        }
    ])

    df["QoH Score"] = (
        df["JD Match"] * w_jd +
        df["Reference"] * w_ref +
        df["Behavior"] * w_beh +
        df["Skill"] * w_skill
    ) / total

    df = df.sort_values("QoH Score", ascending=False)
    st.subheader("📊 Candidate Comparison Table")
    st.dataframe(df[["Candidate", "JD Match", "Reference", "Behavior", "Skill", "QoH Score", "Gaps", "Verified"]], use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 AI Recommendations")
    for _, row in df.iterrows():
        if row["QoH Score"] >= 90:
            st.success(f"{row['Candidate']}: Strong hire. Green light.")
        elif row["Reference"] < 75:
            st.warning(f"{row['Candidate']}: ⚠️ Weak reference. Needs follow-up.")
        elif row["Skill"] < 80:
            st.info(f"{row['Candidate']}: Needs support in **{row['Gaps']}**.")
        else:
            st.write(f"{row['Candidate']}: Ready for interviews.")

# --- LOGIN ---
def login_ui():
    st.markdown("##")
    st.image("A41A3441-9CCF-41D8-8932-25DB5A9176ED.PNG", width=350)
    st.markdown("### From Rejection to Revolution")
    st.caption("💡 I didn’t get the job. I built the platform that fixes the problem.")

    st.markdown("---")
    st.sidebar.header("🔐 Log In or Create Account")
    mode = st.sidebar.radio("Choose Mode", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if mode == "Login" and st.sidebar.button("Log In"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.supabase_user = res.user
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")
    elif mode == "Sign Up" and st.sidebar.button("Register"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("✅ Account created! Check your email for verification.")
        except Exception as e:
            st.error(f"Signup failed: {e}")

# --- ROUTING ---
if st.session_state.supabase_user:
    profile_selector()
    view = st.sidebar.radio("Choose Portal", ["Candidate", "Recruiter"])
    if view == "Candidate":
        candidate_journey()
    else:
        recruiter_dashboard()
else:
    login_ui()
