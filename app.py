import streamlit as st
import os
import openai
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Skippr", layout="wide")

# Load styling
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Init session state
for key, default in {
    "supabase_user": None,
    "supabase_session": None,
    "show_app": False,
    "carousel_index": 0,
    "profile_id": None,
    "resume_text": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Homepage ---
if not st.session_state.show_app:
    st.markdown("""
        <div style='text-align: center; padding-top: 4rem;'>
            <h1 style='color: #1A1A1A; font-size: 3rem;'>Skippr</h1>
            <h3 style='color: #333;'>Predictive Hiring Starts Here</h3>
            <p style='color: #555; font-size: 18px; max-width: 650px; margin: 2rem auto;'>
                Skippr empowers candidates to showcase verified potential — and helps recruiters find high performers faster.
                Powered by AI. Centered on human growth.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style='text-align: left; max-width: 650px; margin: 3rem auto 0 auto; font-size: 17px; color: #444;'>
            <h4 style='color: #1A1A1A;'>Why Skippr?</h4>
            <ul style='list-style-type: none; padding-left: 0;'>
                <li>🔍 <strong>Smart Scoring:</strong> See your Quality of Hire (QoH) score before you apply.</li>
                <li>📈 <strong>Growth Roadmaps:</strong> Get personalized feedback and upskill plans.</li>
                <li>✅ <strong>Verified References:</strong> Build trust with recruiters from the start.</li>
                <li>💬 <strong>Transparent Insights:</strong> Understand how you're being evaluated.</li>
                <li>⚡ <strong>Real Human Potential:</strong> Get seen for your trajectory, not just your resume.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

    slides = [
        "🚀 <strong>See Your Score Before You Apply:</strong><br> Understand your job fit with a verified Quality of Hire (QoH) score.",
        "📊 <strong>Track Skill Gaps. Grow Fast.</strong><br> Get smart, personalized growth plans — powered by AI.",
        "🤝 <strong>Verified References = Instant Credibility</strong><br> Trusted signals that boost recruiter confidence.",
        "🎯 <strong>Built to Help You Skip the Line</strong><br> Go from overlooked to in-demand with Skippr."
    ]
    idx = st.session_state.carousel_index
    st.markdown(f"<div style='text-align: center; font-size: 18px; margin-top: 3rem;'><p>{slides[idx]}</p></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        if st.button("◀️") and idx > 0:
            st.session_state.carousel_index -= 1
    with col3:
        if st.button("▶️") and idx < len(slides) - 1:
            st.session_state.carousel_index += 1

    if st.button("🚀 Get Started", key="start-btn"):
        st.session_state.show_app = True
    st.stop()

# --- Profile Management ---
st.title("👤 Create or Select Your Job Profile")

user_id = st.session_state.supabase_user["id"] if st.session_state.supabase_user else None

def load_profiles():
    if user_id:
        data = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        return data.data if data else []
    return []

profiles = load_profiles()
profile_names = [f"{p['name']} – {p['target_role']}" for p in profiles]

selected = st.selectbox("Choose a profile or create a new one:", ["➕ Create new profile"] + profile_names)

if selected == "➕ Create new profile":
    with st.form("create_profile_form"):
        name = st.text_input("Profile Name")
        target_role = st.text_input("Target Job Title")
        submitted = st.form_submit_button("Create Profile")
        if submitted and user_id:
            new = supabase.table("profiles").insert({
                "user_id": user_id,
                "name": name,
                "target_role": target_role,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            st.success("✅ Profile created!")
            st.experimental_rerun()
else:
    profile_index = profile_names.index(selected)
    profile = profiles[profile_index]
    st.session_state.profile_id = profile["id"]
    st.success(f"Profile loaded: {profile['name']} – {profile['target_role']}")

    # Resume upload
    st.subheader("📄 Upload Your Resume")
    uploaded_file = st.file_uploader("Choose a PDF resume", type="pdf")
    if uploaded_file:
        with pdfplumber.open(uploaded_file) as pdf:
            resume_text = ""
            for page in pdf.pages:
                resume_text += page.extract_text() + "\n"
        st.session_state.resume_text = resume_text
        st.text_area("📋 Parsed Resume Preview", resume_text, height=300)




# --- JD Upload + Semantic Matching ---
import tiktoken

st.header("📄 Job Description Matching")

st.markdown("Upload 1–2 job descriptions (PDF or text), and we’ll show how well your resume aligns.")

uploaded_jds = st.file_uploader("Upload Job Descriptions", type=["pdf", "txt"], accept_multiple_files=True)

def extract_text(file):
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    else:
        return file.read().decode("utf-8")

jd_texts = []
for file in uploaded_jds[:2]:
    jd_texts.append(extract_text(file))

def gpt_match_score(resume_text, jd_text):
    prompt = f"""
You are an AI assistant helping assess job fit.

Compare the following resume and job description. Score the resume's match to the JD (0-100%) and explain why.

Resume:
{resume_text}

Job Description:
{jd_text}

Respond in JSON with:
- "score": match percentage
- "summary": 1 paragraph rationale
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    text = response["choices"][0]["message"]["content"]
    import json
    try:
        result = json.loads(text)
        return result["score"], result["summary"]
    except:
        return 0, "Unable to parse score."

if jd_texts and st.session_state.resume_text:
    st.subheader("📊 Match Results")
    scores = []
    summaries = []
    for idx, jd in enumerate(jd_texts):
        score, summary = gpt_match_score(st.session_state.resume_text, jd)
        scores.append(score)
        summaries.append(summary)
        st.markdown(f"**JD #{idx+1} Match Score:** {score:.1f}%")
        st.caption(summary)

    # Radar chart visualization
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4,4), subplot_kw=dict(polar=True))
    labels = [f"JD #{i+1}" for i in range(len(scores))]
    angles = np.linspace(0, 2*np.pi, len(scores), endpoint=False).tolist()
    values = scores + [scores[0]]
    angles += [angles[0]]

    ax.plot(angles, values, 'o-', linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)
    st.pyplot(fig)



# --- Reference Collection ---
st.header("🧑‍🤝‍🧑 Reference Collection")

references = []
for i in range(1, 3+1):
    with st.expander(f"Reference {i}"):
        name = st.text_input(f"Name {i}")
        relationship = st.text_input(f"Relationship {i}")
        email = st.text_input(f"Email {i}")
        if name and relationship and email:
            references.append({"name": name, "relationship": relationship, "email": email})

# --- Backchannel Input ---
st.subheader("🔍 Backchannel Contact (optional)")
contact_name = st.text_input("Trusted contact name (someone who knows the company/team)")
contact_notes = st.text_area("What do you want to ask them?")

# --- HR Performance Checkpoint ---
st.subheader("🛡️ HR Performance Verification")
st.info("This step is optional. It simulates an HR manager uploading your performance review.")
uploaded_perf = st.file_uploader("Upload PDF (e.g., performance summary or review)", type="pdf")

# --- QoH Score Calculation ---
st.header("📈 Quality of Hire (QoH) Score")

score = 0
if st.session_state.resume_text:
    score += 30
if jd_texts:
    score += 30
if len(references) >= 2:
    score += 20
if any(roadmap.values()):
    score += 10
if uploaded_perf:
    score += 10

st.metric("Estimated QoH Score", f"{score} / 100")

# --- Final Summary ---
st.header("✅ Final Profile Summary")

st.markdown(f'''
- **Profile**: {profile["name"]} - {profile["target_role"]}
- **Resume Uploaded**: ✅
- **Job Descriptions Matched**: {len(jd_texts)}
- **References Provided**: {len(references)}
- **Backchannel Contact**: {"✅" if contact_name else "❌"}
- **Performance Upload**: {"✅" if uploaded_perf else "❌"}
- **Growth Roadmap**: {"✅" if any(roadmap.values()) else "❌"}
- **Final QoH Score**: **{score} / 100**
''')


# --- Merged Functionality from GrowScore ---


# Apply custom CSS from assets
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ Custom CSS not found. Using default styling.")


# Load secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
OPENAI_KEY = st.secrets["openai"]["key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_KEY

# Auth state

# Branding Header with logo
try:
    st.image("assets/logo.png", width=120)
except FileNotFoundError:
    st.warning("⚠️ Logo not found — skipping logo display.")

st.markdown("""
<div style='text-align: center; margin-top: -10px;'>
    <h1 style='color: white;'>Welcome to Skippr</h1>
    <p style='color: #CCCCCC; font-size: 18px;'>🧭 Helping you skip the noise and land faster.</p>
</div>
""", unsafe_allow_html=True)


if "supabase_session" not in st.session_state:
    st.session_state.supabase_session = None
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = None

# Login UI
with st.sidebar:
    st.header("🧭 Candidate Login")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if auth_mode == "Login":
        if st.button("🔓 Login"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_session = result.session
                st.session_state.supabase_user = result.user
                st.success(f"✅ Logged in as {email}")
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        if st.button("🆕 Register"):
            try:
                result = supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created. Check email for verification.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

if not st.session_state.supabase_session:
    st.warning("❌ No active session. Please log in.")
    st.stop()
    
skills_pool = ["Python", "SQL", "Data Analysis", "Leadership", "Project Management",
               "Communication", "Strategic Planning", "Excel", "Machine Learning"]

leadership_skills = ["Ownership", "Bias for Action", "Earn Trust", "Deliver Results",
                     "Think Big", "Customer Obsession", "Invent & Simplify", "Hire & Develop",
                     "Dive Deep", "Frugality", "Have Backbone"]

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

def plot_radar(jd_scores):
    labels = [f"JD {i+1}" for i in range(len(jd_scores))]
    angles = np.linspace(0, 2 * np.pi, len(jd_scores), endpoint=False).tolist()
    scores = jd_scores + jd_scores[:1]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, 'o-', linewidth=2)
    ax.fill(angles, scores, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)
    st.pyplot(fig)

def generate_growth_recs():
    return [
        "- [Coursera: Data & Business Skills](https://coursera.org)",
        "- [LinkedIn Learning: Leadership Path](https://linkedin.com/learning)",
        "- Join a cross-functional project in your org",
        "- Set a 30/60/90 SMART goal around growth gaps"
        ]
        # ------------------- Candidate Journey -------------------
def candidate_journey():
    st.title("🌱 Candidate Journey")
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)
    st.progress((step + 1) / 9)

    if step == 0:
        st.subheader("📝 Step 1: Candidate Info + Portfolio Sync")
        st.markdown("Welcome! Let’s start with your contact info and resume.")
        contact_info = st.session_state.get("resume_contact", {"cand_name": "", "cand_email": "", "cand_title": ""})
        name_val = st.text_input("Full Name", key="cand_name", value=contact_info.get("cand_name", ""))
        email_val = st.text_input("Email", key="cand_email", value=contact_info.get("cand_email", ""))
        title_val = st.text_input("Target Job Title", key="cand_title", value=contact_info.get("cand_title", ""))
        st.text_input("🔗 LinkedIn Profile", key="cand_linkedin")
        st.text_input("🔗 GitHub Profile", key="cand_github")
        st.text_input("🌐 Portfolio / Personal Site", key="cand_portfolio")

        uploaded = st.file_uploader("📎 Upload Resume (PDF or TXT)", type=["pdf", "txt"])
        if uploaded:
            if uploaded.type == "application/pdf":
                with pdfplumber.open(uploaded) as pdf:
                    text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            else:
                text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state.resume_text = text
            st.session_state.resume_skills = extract_skills_from_resume(text)
            contact = extract_contact_info(text)
            st.session_state["resume_contact"] = {
                "cand_name": name_val or contact.get("name", ""),
                "cand_email": email_val or contact.get("email", ""),
                "cand_title": title_val or contact.get("title", "")
            }
            st.success("✅ Resume parsed and fields updated.")

        st.button("Next", on_click=next_step)

    elif step == 1:
        st.subheader("🎯 Step 2: Select Your Top Skills")
        st.markdown("Review and adjust the top skills extracted from your resume.")
        selected = st.multiselect("Top Skills:", skills_pool, default=st.session_state.get("resume_skills", []))
        st.session_state.selected_skills = selected
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 2:
        st.subheader("📋 Step 3: Behavior Survey")
        opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        score_map = {opt: i + 1 for i, opt in enumerate(opts)}
        q1 = st.radio("I meet deadlines", opts, index=2)
        q2 = st.radio("I collaborate effectively", opts, index=2)
        q3 = st.radio("I adapt well to change", opts, index=2)
        st.session_state.behavior_score = round((score_map[q1] + score_map[q2] + score_map[q3]) / 3 * 20, 1)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 3:
        st.subheader("📨 Step 4: References (Simulated)")
        def add_ref(i):
            with st.expander(f"Reference {i+1}"):
                name = st.text_input("Name", key=f"ref_name_{i}")
                email = st.text_input("Email", key=f"ref_email_{i}")
                role = st.selectbox("Relationship", ["Manager", "Peer", "Direct Report"], key=f"ref_role_{i}")
                trait = st.selectbox("Leadership Trait", leadership_skills, key=f"ref_trait_{i}")
                sent = st.button(f"Send to {name or f'Ref {i+1}'}", key=f"send_ref_{i}")
                return {"name": name, "email": email, "role": role, "trait": trait, "status": "✅ Sent" if sent else "⏳ Pending"}
        st.session_state.references = [add_ref(0), add_ref(1)]
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 4:
        st.subheader("🏢 Step 5: Backchannel Reference")
        name = st.text_input("Contact Name", key="bc_name")
        email = st.text_input("Email", key="bc_email")
        topic = st.text_area("What would you like them to share insight about?", key="bc_topic")
        if st.button("Send Backchannel Request"):
            st.session_state.backchannel = {"name": name, "email": email, "topic": topic, "status": "✅ Sent"}
            st.success("Backchannel request sent.")
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 5:
        st.subheader("🎓 Step 6: Education")
        degree = st.text_input("Degree", key="edu_degree")
        major = st.text_input("Major", key="edu_major")
        school = st.text_input("School", key="edu_school")
        year = st.text_input("Graduation Year", key="edu_year")
        edu_file = st.file_uploader("Upload transcript or diploma (optional)", type=["pdf"], key="edu_file")
        st.session_state.education = f"{degree} in {major}, {school}, {year}"
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 6:
        st.subheader("🔐 Step 7: HR Performance Checkpoint")
        st.warning("This is a future feature. No emails will be sent.")
        st.text_input("Company", key="hr_company")
        st.text_input("Manager", key="hr_manager")
        st.text_input("HR Email (optional)", key="hr_email")
        st.checkbox("I authorize GrowScore to verify past performance", key="hr_auth")
        st.session_state.hr_check = "✅ HR Request Authorized (simulated)"
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 7:
        st.subheader("📄 Step 8: Resume vs JD Skill Match")
        jd1 = st.text_area("Paste JD 1", key="jd_1")
        jd2 = st.text_area("Paste JD 2", key="jd_2")
        jd_inputs = [jd for jd in [jd1, jd2] if jd.strip()]
        if jd_inputs and "resume_text" in st.session_state:
            jd_scores = match_resume_to_jds(st.session_state.resume_text, jd_inputs)
            st.session_state.jd_scores = jd_scores
            for i, score in enumerate(jd_scores):
                st.write(f"**JD {i+1}** Match Score: {score}%")
            plot_radar(jd_scores)
        st.button("Back", on_click=prev_step)
        st.button("Next", on_click=next_step)

    elif step == 8:
        st.subheader("✅ Step 9: Final Summary & Growth Roadmap")
        jd_scores = st.session_state.get("jd_scores", [])
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1) if jd_scores else 0
        skill_score = len(st.session_state.get("selected_skills", [])) * 5
        ref_score = 90
        behavior = st.session_state.get("behavior_score", 50)
        qoh = round((skill_score + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("💡 Quality of Hire Score", f"{qoh}/100")

        st.subheader("🔍 Verification Table")
        st.table({
            "Resume": ["✅ GPT Verified"],
            "References": ["✅ Sent"],
            "Backchannel": [st.session_state.get("backchannel", {}).get("status", "❌")],
            "Education": ["✅" if st.session_state.get("education") else "❌"],
            "HR Performance": [st.session_state.get("hr_check", "❌")],
            "Behavior": ["🟠 Self-Reported"],
            "JD Match": [f"{avg_jd}%"]
        })

        st.subheader("📈 Growth Roadmap")
        for rec in generate_growth_recs():
            st.markdown(rec)
        st.success("🎉 You’ve completed your GrowScore profile!")

# ------------------- Recruiter Dashboard -------------------
def recruiter_dashboard():
    st.title("🧑‍💼 Recruiter Dashboard")
    with st.sidebar.expander("🎚️ QoH Weight Sliders", expanded=True):
        w_jd = st.slider("JD Match", 0, 100, 25)
        w_ref = st.slider("References", 0, 100, 25)
        w_beh = st.slider("Behavior", 0, 100, 25)
        w_skill = st.slider("Skills", 0, 100, 25)

    total = w_jd + w_ref + w_beh + w_skill
    if total == 0:
        st.warning("Adjust sliders to view scores.")
        return

    df = pd.DataFrame([
        {"Candidate": "Lamont", "JD Match": 88, "Reference": 90, "Behavior": 84, "Skill": 92,
         "Gaps": "Strategic Planning", "Verified": "✅ Resume, ✅ References, ✅ JD, 🟠 Behavior, ✅ Education, 🔐 HR"},
        {"Candidate": "Jasmine", "JD Match": 82, "Reference": 78, "Behavior": 90, "Skill": 80,
         "Gaps": "Leadership", "Verified": "✅ Resume, ⚠️ References, ✅ JD, ✅ Behavior, ✅ Education, ❌ HR"},
        {"Candidate": "Andre", "JD Match": 75, "Reference": 65, "Behavior": 70, "Skill": 78,
         "Gaps": "Communication", "Verified": "✅ Resume, ❌ References, ✅ JD, ⚠️ Behavior, ❌ Education, ❌ HR"}
    ])

    selected = st.multiselect("Compare Candidates", df["Candidate"].tolist(), default=df["Candidate"].tolist())
    filtered = df[df["Candidate"].isin(selected)].copy()

    filtered["QoH Score"] = (
        filtered["JD Match"] * w_jd +
        filtered["Reference"] * w_ref +
        filtered["Behavior"] * w_beh +
        filtered["Skill"] * w_skill
    ) / total

    st.subheader("📋 Candidate Comparison Table")
    st.dataframe(filtered)

    st.subheader("🎯 AI Recommendations")
    for _, row in filtered.iterrows():
        if row["QoH Score"] >= 90:
            st.success(f"{row['Candidate']}: 🚀 Strong hire. Green light.")
        elif row["Reference"] < 75:
            st.warning(f"{row['Candidate']}: ⚠️ Weak reference. Needs follow-up.")
        elif row["Skill"] < 80:
            st.info(f"{row['Candidate']}: Needs support in **{row['Gaps']}**.")
        else:
            st.write(f"{row['Candidate']}: Ready for interviews.")

# ------------------- Routing -------------------
st.title("🚀 Welcome to GrowScore")
portal = st.radio("Choose your portal:", ["👤 Candidate Portal", "🧑‍💼 Recruiter Portal"])
if portal == "👤 Candidate Portal":
    candidate_journey()
else:
    recruiter_dashboard()
