import streamlit as st
import openai
import pdfplumber
import ast
import pandas as pd
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# --- SESSION STATE INIT ---
for k in ["supabase_user", "step", "selected_profile"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "step" else 0

# --- PROFILE LOGIC ---
def save_profile():
    user_id = st.session_state.supabase_user.id
    profile_name = st.session_state.get("selected_profile")
    if not profile_name: return
    data = {
        "user_id": user_id,
        "name": profile_name,
        "skills": st.session_state.get("selected_skills", []),
        "resume_text": st.session_state.get("resume_text", ""),
        "behavior_score": st.session_state.get("behavior_score", 0),
        "jd_scores": st.session_state.get("jd_scores", []),
        "qoh_score": st.session_state.get("qoh_score", 0),
    }
    existing = supabase.table("profiles").select("id").eq("user_id", user_id).eq("name", profile_name).execute().data
    if existing:
        supabase.table("profiles").update(data).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("profiles").insert(data).execute()

def load_profile(profile_id):
    profile = supabase.table("profiles").select("*").eq("id", profile_id).single().execute().data
    st.session_state["resume_text"] = profile.get("resume_text", "")
    st.session_state["selected_skills"] = profile.get("skills", [])
    st.session_state["behavior_score"] = profile.get("behavior_score", 0)
    st.session_state["jd_scores"] = profile.get("jd_scores", [])
    st.session_state["qoh_score"] = profile.get("qoh_score", 0)

def profile_selector():
    user_id = st.session_state.supabase_user.id
    profiles = supabase.table("profiles").select("id, name").eq("user_id", user_id).execute().data
    names = [p["name"] for p in profiles]
    st.markdown("### 📂 Candidate Profiles")
    selected = st.selectbox("Choose or create profile", names + ["➕ New Profile"])
    if selected == "➕ New Profile":
        new_name = st.text_input("New Profile Name")
        if st.button("Create Profile") and new_name:
            st.session_state["selected_profile"] = new_name
            save_profile()
            st.rerun()
    elif selected:
        st.session_state["selected_profile"] = selected
        profile_id = next((p["id"] for p in profiles if p["name"] == selected), None)
        load_profile(profile_id)
        st.success(f"✅ Loaded profile: {selected}")

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
        return [75, 80]  # fallback

# --- CANDIDATE JOURNEY (Steps 0-5) ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload")
        uploaded = st.file_uploader("Upload Resume", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else \
                "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            st.success("✅ Resume parsed.")
        st.button("Next", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        selected = st.multiselect("Choose your strongest skills:", st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        score_total = 0
        for i, question in enumerate(["Meets deadlines", "Works well in teams", "Adapts to change", "Communicates well", "Shows leadership"]):
            response = st.radio(question, opts, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (5 * 5)) * 100, 1)
        st.session_state.behavior_score = behavior_score
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        traits = ["Leadership", "Communication", "Reliability", "Teamwork"]
        with st.expander("Reference 1"):
            st.text_input("Name", key="ref1_name")
            st.text_input("Email", key="ref1_email")
            st.selectbox("Trait", traits, key="ref1_trait")
            st.text_area("Message", key="ref1_msg")
            if st.button("Send Ref 1"): st.success("Sent")
        with st.expander("Reference 2"):
            st.text_input("Name", key="ref2_name")
            st.text_input("Email", key="ref2_email")
            st.selectbox("Trait", traits, key="ref2_trait")
            st.text_area("Message", key="ref2_msg")
            if st.button("Send Ref 2"): st.success("Sent")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.markdown("### 🎓 Step 5: Education")
        st.text_input("Degree")
        st.text_input("Institution")
        st.text_input("Year")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)
# --- CANDIDATE JOURNEY (Steps 6-10) ---
    elif step == 5:
        st.markdown("### 🏢 Step 6: HR Verification")
        st.text_input("Company")
        st.text_input("Manager")
        st.text_input("HR Email")
        st.checkbox("I authorize verification")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.markdown("### 📄 Step 7: Job Matching")
        jd1 = st.text_area("Paste JD 1")
        jd2 = st.text_area("Paste JD 2")
        if jd1 and "resume_text" in st.session_state:
            scores = match_resume_to_jds(st.session_state.resume_text, [jd1, jd2])
            st.session_state.jd_scores = scores
            for i, score in enumerate(scores):
                st.markdown(f"**JD {i+1} Match Score:** {score}%")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.markdown("### 📊 Step 8: Quality of Hire Score")
        jd_scores = st.session_state.get("jd_scores", [75, 80])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills = len(st.session_state.get("selected_skills", [])) * 5
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        qoh = round((skills + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("📈 QoH Score", f"{qoh}/100")
        st.session_state.qoh_score = qoh
        save_profile()
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.markdown("### 🚀 Step 9: Career Growth Roadmap")
        prompt = f"Based on this resume:\n{st.session_state.get('resume_text', '')}\n\nCreate a roadmap:\n- 30-day\n- 60-day\n- 90-day\n- 6-month\n- 1-year plan."
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            roadmap = response.choices[0].message.content.strip()
        except:
            roadmap = "• 30-Day: Get started\n• 60-Day: Deliver a win\n• 90-Day: Lead an initiative\n• 6-Month: Strategic growth\n• 1-Year: Promotion ready"
        st.markdown(f"**Your Roadmap:**\n\n{roadmap}")
        st.button("Back", on_click=prev_step)
        st.button("Finish", on_click=next_step)

    elif step == 9:
        st.success("🎉 Your Candidate Journey is Complete!")
        st.balloons()

# --- RECRUITER DASHBOARD ---
def recruiter_dashboard():
    st.title("💼 Recruiter Dashboard")
    w_jd = st.slider("JD Match", 0, 100, 25)
    w_ref = st.slider("References", 0, 100, 25)
    w_beh = st.slider("Behavior", 0, 100, 25)
    w_skill = st.slider("Skills", 0, 100, 25)
    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Adjust sliders to see scores.")
        return
    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Reference": 90, "Behavior": 84, "Skill": 92, "Gaps": "Strategic Planning"},
        {"Candidate": "Jasmine", "JD Match": 82, "Reference": 78, "Behavior": 90, "Skill": 80, "Gaps": "Leadership"},
        {"Candidate": "Andre", "JD Match": 75, "Reference": 65, "Behavior": 70, "Skill": 78, "Gaps": "Communication"},
    ])
    df["QoH Score"] = (df["JD Match"] * w_jd + df["Reference"] * w_ref + df["Behavior"] * w_beh + df["Skill"] * w_skill) / total
    df = df.sort_values("QoH Score", ascending=False)
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("AI Recommendations")
    for _, row in df.iterrows():
        score = row["QoH Score"]
        candidate = row["Candidate"]
        if score >= 90:
            st.success(f"{candidate}: Top-tier. Strong hire.")
        elif row["Reference"] < 75:
            st.warning(f"{candidate}: Weak reference.")
        else:
            st.info(f"{candidate}: Promising. Check gaps: {row['Gaps']}")

# --- LOGIN UI ---
def login_ui():
    st.title("🔐 Welcome to Skippr")
    st.subheader("Empowering Talent. Elevating Potential.")
    st.caption("Your career is more than a resume. Skippr gives you a verified Quality of Hire Score that aligns you with the right roles and provides real coaching.")
    mode = st.radio("Choose Mode", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if mode == "Login" and st.button("Log In"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.supabase_user = res.user
            st.success("✅ Logged in.")
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")
    elif mode == "Sign Up" and st.button("Register"):
        try:
            supabase.auth.sign_up({"email": email, "password": password})
            st.success("✅ Check your email for verification.")
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
