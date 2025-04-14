
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
