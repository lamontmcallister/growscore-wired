import streamlit as st
import ast
import json
import pdfplumber
import pandas as pd
from supabase import Client
from datetime import datetime
from db.client import get_supabase_client
from ai.client import get_openai_client
from ai.resume import call_openai_json, extract_skills_from_resume, extract_contact_info, match_resume_to_jds, match_resume_to_jd
from ai.learning_resources import coursera_search_link
from auth.roles import get_user_role

# --- CONFIG ---
st.set_page_config(page_title="Skippr", layout="wide")

supabase: Client = get_supabase_client()
openai_client = get_openai_client()

# --- CUSTOM STYLING ---
def load_custom_css():
    st.markdown("""
        <style>
            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }
            .stApp {
                background: radial-gradient(ellipse 1200px 600px at 50% -10%, rgba(45,91,255,0.08), transparent),
                            radial-gradient(ellipse 800px 500px at 90% 10%, rgba(0,194,168,0.06), transparent),
                            #F7F8FA;
            }
            h1, h2, h3 {
                font-weight: 700 !important;
                color: #16181D !important;
                letter-spacing: -0.02em;
            }
            p, label, .stMarkdown, .stCaption {
                color: #3A3F47;
            }
            /* Buttons: pill-shaped, cool blue */
            div.stButton > button {
                background: linear-gradient(135deg, #2D5BFF, #00C2A8);
                color: #FFFFFF;
                border: none;
                border-radius: 24px;
                padding: 0.55rem 1.4rem;
                font-weight: 600;
                font-size: 0.95rem;
                transition: filter 0.15s ease, transform 0.1s ease;
            }
            div.stButton > button:hover {
                filter: brightness(1.08);
                transform: translateY(-1px);
                color: #FFFFFF;
            }
            div.stButton > button p {
                color: #FFFFFF !important;
                font-weight: 600 !important;
            }
            /* Sidebar: white panel, hairline border */
            section[data-testid="stSidebar"] {
                background-color: #FFFFFF;
                border-right: 1px solid #E4E6EA;
            }
            /* Card-style sections, matching LinkedIn's white content cards */
            div[data-testid="stHorizontalBlock"],
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #FFFFFF;
                border: 1px solid #E4E6EA;
                border-radius: 12px;
                padding: 1.25rem 1.5rem;
                box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
                margin-bottom: 1rem;
            }
            /* Inputs */
            input, textarea, select {
                border-radius: 8px !important;
                border: 1px solid #D7DAE0 !important;
            }
            input:focus, textarea:focus {
                border-color: #2D5BFF !important;
                box-shadow: 0 0 0 2px rgba(45, 91, 255, 0.15) !important;
            }
            /* Progress bar: gradient pill */
            div[data-testid="stProgress"] > div {
                border-radius: 999px;
                background-color: #E4E6EA;
            }
            div[data-testid="stProgress"] > div > div {
                background: linear-gradient(90deg, #2D5BFF, #00C2A8);
                border-radius: 999px;
            }
            /* Data tables (recruiter dashboard) */
            div[data-testid="stDataFrame"] {
                border: 1px solid #E4E6EA;
                border-radius: 8px;
                overflow: hidden;
            }
            /* Alert boxes */
            div[data-testid="stAlert"] {
                border-radius: 8px;
            }
            .markdown-block {
                background-color: #FFFFFF;
                padding: 1rem 1.5rem;
                border-radius: 12px;
                border: 1px solid #E4E6EA;
                margin-bottom: 1rem;
            }
            /* Sliders: brand blue instead of default red */
            div[data-testid="stSlider"] div[role="slider"] {
                background-color: #2D5BFF !important;
                border-color: #2D5BFF !important;
            }
            div[data-testid="stSlider"] > div > div > div {
                background: linear-gradient(90deg, #2D5BFF, #00C2A8) !important;
            }
            /* QoH score badge pills */
            .qoh-badge {
                display: inline-block;
                padding: 0.25rem 0.7rem;
                border-radius: 999px;
                font-weight: 700;
                font-size: 0.85rem;
            }
            .qoh-high { background-color: #DCFCE7; color: #15803D; }
            .qoh-mid { background-color: #DBEAFE; color: #1D4ED8; }
            .qoh-low { background-color: #FEF3C7; color: #B45309; }
            .qoh-incomplete { background-color: #F1F2F5; color: #6B7280; }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# --- SESSION STATE ---
for k in ["supabase_session", "supabase_user", "step", "profiles", "active_profile", "profile_selected"]:
    if k not in st.session_state:
        if k == "step":
            st.session_state[k] = 0
        elif k == "profiles":
            st.session_state[k] = {}
        elif k == "profile_selected":
            st.session_state[k] = False
        else:
            st.session_state[k] = None

# --- HELPER FUNCTIONS ---
def ensure_profile_initialized(profile_name):
    if profile_name not in st.session_state.profiles:
        st.session_state.profiles[profile_name] = {"progress": {}}

skills_pool = [
    "Python", "SQL", "Leadership", "Data Analysis", "Machine Learning",
    "Communication", "Strategic Planning", "Excel", "Project Management"
]

def calculate_qoh_score(skill_count, ref, behav, jd_scores):
    if not jd_scores:
        return None, None
    avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
    skills = min(skill_count * 5, 100)
    final = round((skills + ref + behav + avg_jd) / 4, 1)
    return final, {"Skills": skills, "References": ref, "Behavior": behav, "JD Match": avg_jd}


# --- PROFILE MANAGEMENT ---
def profile_management():
    st.title("👤 Profile Management")
    user_email = st.session_state.supabase_user.email
    try:
        profiles = supabase.table("profiles").select("*").eq("user_email", user_email).execute()
    except Exception as e:
        st.error(f"❌ Failed to fetch profiles: {e}")
        st.stop()

    profile_names = [p["name"] for p in profiles.data] if profiles.data else []
    st.write("Choose a profile or create a new one:")

    selected = st.selectbox("Select Profile", ["Create New"] + profile_names if profile_names else ["Create New"])

    if selected == "Create New":
        new_name = st.text_input("Enter New Profile Name")
        if st.button("Start with New Profile") and new_name:
            if new_name in profile_names:
                st.warning("Profile name already exists. Choose another name.")
            else:
                profile_data = {
                    "user_email": user_email,
                    "name": new_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    supabase.table("profiles").insert(profile_data).execute()
                    st.success(f"✅ New profile '{new_name}' created successfully!")
                    st.session_state.active_profile = new_name
                    st.session_state.step = 0
                    st.session_state.profile_selected = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating profile: {e}")
    elif selected:
        st.session_state.active_profile = selected
        st.session_state.step = 0
        st.session_state.profile_selected = True
        profile_data = next((p for p in profiles.data if p["name"] == selected), {})
        st.write(f"**Job Title**: {profile_data.get('job_title', 'N/A')}")
        st.write(f"**QoH Score**: {profile_data.get('qoh_score', 'N/A')}")
        if st.button(f"Edit Profile: {selected}"):
            st.rerun()
        if st.button(f"Delete Profile: {selected}"):
            try:
                supabase.table("profiles").delete().eq("name", selected).eq("user_email", user_email).execute()
                st.success(f"Deleted profile: {selected}")
                st.session_state.profile_selected = False
                st.session_state.active_profile = None
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete profile: {e}")


# --- CANDIDATE JOURNEY ---
def candidate_journey():
    step = st.session_state.get("step", 0)
    def next_step(): st.session_state.step = step + 1
    def prev_step(): st.session_state.step = max(0, step - 1)

    st.markdown("""
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:1.2rem;">
            <div style="width:32px;height:32px;background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                        border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <span style="color:#FFFFFF;font-weight:800;font-size:1rem;">S</span>
            </div>
            <span style="font-size:1.15rem;font-weight:800;letter-spacing:-0.02em;
                         background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                         -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                         background-clip:text;">Skippr</span>
        </div>
    """, unsafe_allow_html=True)
    st.title("🚀 Candidate Journey")
    st.progress((step + 1) / 10)

    if step == 0:
        st.markdown("### 📝 Step 1: Resume Upload + Contact Info")
        st.markdown("""_We'll use your resume to extract relevant skills and auto-fill your contact info. You control what gets shared._""")
        st.text_input("Full Name", key="cand_name")
        st.text_input("Email", key="cand_email")
        st.text_input("Target Job Title", key="cand_title")
        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text

            with st.spinner("Extracting skills..."):
                skills, skills_error = extract_skills_from_resume(text)
            if skills_error:
                st.warning(f"⚠️ Couldn't auto-extract skills ({skills_error}). You can still select them manually below.")
                st.session_state.resume_skills = []
            else:
                st.session_state.resume_skills = skills

            with st.spinner("Extracting contact info..."):
                contact, contact_error = extract_contact_info(text)
            if contact_error:
                st.warning(f"⚠️ Couldn't auto-extract contact info ({contact_error}). Please fill it in manually above.")
            else:
                st.session_state.resume_contact = contact

            st.success("✅ Resume parsed.")
        st.button("Skip →", on_click=next_step)

    elif step == 1:
        st.markdown("### 📋 Step 2: Select Your Skills")
        st.markdown("""_These skills help recruiters understand your strengths. Adjust or add based on what best represents you._""")
        resume_skills = st.session_state.get("resume_skills", [])
        # Build the options list from the fixed pool PLUS whatever the AI
        # extracted from this resume, so multiselect's default never
        # references a value that isn't in its own options (Streamlit
        # raises StreamlitAPIException if that happens).
        available_skills = list(dict.fromkeys(skills_pool + resume_skills))
        selected = st.multiselect("Choose your strongest skills:", available_skills, default=resume_skills)
        st.session_state.selected_skills = selected
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 2:
        st.markdown("### 🧠 Step 3: Behavioral Survey")
        st.markdown("""_This survey helps highlight how you work. It's part of your Quality of Hire score._""")
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
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 3:
        st.markdown("### 🤝 Step 4: References")
        st.markdown("""_References build credibility. These are private and only used to strengthen your application._""")
        traits = ["Leadership", "Communication", "Reliability", "Strategic Thinking", "Teamwork", "Adaptability", "Problem Solving", "Empathy", "Initiative", "Collaboration"]
        for i in range(1, 3):
            with st.expander(f"Reference {i}"):
                st.text_input("Name", key=f"ref{i}_name")
                st.text_input("Email", key=f"ref{i}_email")
                st.selectbox("Trait to Highlight", traits, key=f"ref{i}_trait")
                st.text_area("Optional Message", key=f"ref{i}_msg")
                if st.button(f"Send to Ref {i}"):
                    st.success(f"Request sent to {st.session_state.get(f'ref{i}_name')}")
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Backchannel (Optional)")
        st.markdown("""_Backchannel input gives you insights into teams or companies from people who've worked there._""")
        st.text_input("Name")
        st.text_input("Email")
        st.text_area("Message or Topic for Feedback")
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education")
        st.markdown("""_Add education details to boost trust and completeness in your profile._""")
        st.text_input("Degree")
        st.text_input("Major")
        st.text_input("Institution")
        st.text_input("Graduation Year")
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 6:
        st.markdown("### 🏢 Step 7: HR Check")
        st.markdown("""_You can request verification from past employers here. It's a future feature — no emails will be sent now._""")
        st.text_input("Company")
        st.text_input("Manager")
        st.text_input("HR Email")
        st.checkbox("I authorize verification")
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 7:
        st.markdown("### 📄 Step 8: Job Matching")
        st.markdown("""_Paste the job description you're targeting. We'll show exactly what matches and what's missing -- not just a score._""")
        jd_target = st.text_area("Paste the job description you're targeting", value=st.session_state.get("jd_target_text", ""), height=200)
        if st.button("Analyze Match") and jd_target and "resume_text" in st.session_state:
            with st.spinner("Analyzing your fit against this role..."):
                match_data, match_error = match_resume_to_jd(st.session_state.resume_text, jd_target)
            if match_error:
                st.error(f"⚠️ Couldn't analyze this match right now ({match_error}). Try again in a moment.")
            else:
                st.session_state.jd_target_text = jd_target
                st.session_state.jd_match_data = match_data
                st.session_state.jd_scores = [match_data.get("score", 0)]

        match_data = st.session_state.get("jd_match_data")
        if match_data:
            st.metric("Match Score", f"{match_data.get('score', 0)}%")
            col_match, col_gap = st.columns(2)
            with col_match:
                st.markdown("**✅ Matched skills**")
                for item in match_data.get("matched_skills", []):
                    skill = item.get("skill", "") if isinstance(item, dict) else item
                    evidence = item.get("evidence", "") if isinstance(item, dict) else ""
                    st.markdown(f"**{skill}**")
                    if evidence:
                        st.caption(f"From your resume: \"{evidence}\"")
            with col_gap:
                st.markdown("**🔍 Skills to develop**")
                for item in match_data.get("missing_skills", []):
                    skill = item.get("skill", "") if isinstance(item, dict) else item
                    why = item.get("why_it_matters", "") if isinstance(item, dict) else ""
                    st.markdown(f"**{skill}**")
                    if why:
                        st.caption(why)

        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 8:
        st.markdown("### 📊 Step 9: Quality of Hire Score")
        st.markdown("""_This is your full Quality of Hire score — built from your skills, behavior, references, and JD match._""")
        jd_scores = st.session_state.get("jd_scores", [])
        skill_count = len(st.session_state.get("selected_skills", []))
        behavior = st.session_state.get("behavior_score", 50)
        ref_score = 90
        qoh, breakdown = calculate_qoh_score(skill_count, ref_score, behavior, jd_scores)
        if qoh is None:
            st.warning("⚠️ No JD match scores yet — go back to Step 8 and paste a job description first.")
        else:
            st.metric("📈 QoH Score", f"{qoh}/100")
            ensure_profile_initialized(st.session_state.active_profile)
            st.session_state.qoh_score = qoh
            st.session_state.profiles[st.session_state.active_profile]["qoh"] = qoh
            st.session_state.profiles[st.session_state.active_profile]["progress"]["Quality of Hire"] = True
            for k, v in breakdown.items():
                st.write(f"**{k}**: {v}/100")
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 9:
        st.markdown("### 🚀 Step 10: Growth Roadmap")

        match_data = st.session_state.get("jd_match_data")
        missing_skills = match_data.get("missing_skills", []) if match_data else []

        if missing_skills:
            st.markdown("""_This roadmap is built around the specific gaps identified in Step 8 -- not generic advice._""")
            gap_lines = "\n".join(
                f"- {item.get('skill', '')}: {item.get('why_it_matters', '')}"
                for item in missing_skills if isinstance(item, dict)
            )
            prompt = (
                f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\n"
                f"This candidate is targeting a specific role and has these skill gaps:\n{gap_lines}\n\n"
                "Create a career roadmap specifically focused on closing THESE gaps, in priority order. "
                "Each phase should reference which specific gap(s) it addresses.\n\n"
                'Respond as JSON: {"30_day": "...", "60_day": "...", "90_day": "...", "6_month": "...", "1_year": "..."}'
            )
        else:
            st.markdown("""_This roadmap gives general 30/60/90-day growth ideas. For a roadmap targeted at a specific role, go back to Step 8 and analyze a job description first._""")
            prompt = (
                f"Given this resume:\n{st.session_state.get('resume_text', '')}\n\n"
                'Create a career roadmap. Respond as JSON: '
                '{"30_day": "...", "60_day": "...", "90_day": "...", "6_month": "...", "1_year": "..."}'
            )

        roadmap_data, roadmap_error = call_openai_json(prompt, temperature=0.7)
        if roadmap_error:
            st.error(f"⚠️ Couldn't generate a roadmap right now ({roadmap_error}). You can still save your profile below.")
            roadmap = None
        else:
            roadmap = roadmap_data
            st.markdown(f"**30-Day:** {roadmap.get('30_day', '')}")
            st.markdown(f"**60-Day:** {roadmap.get('60_day', '')}")
            st.markdown(f"**90-Day:** {roadmap.get('90_day', '')}")
            st.markdown(f"**6-Month:** {roadmap.get('6_month', '')}")
            st.markdown(f"**1-Year:** {roadmap.get('1_year', '')}")
            st.success("🎉 Complete!")

        if missing_skills:
            st.markdown("### 📚 Recommended Learning")
            st.caption("Real search results on Coursera for each gap -- not AI-guessed course names.")
            for item in missing_skills:
                if not isinstance(item, dict):
                    continue
                skill = item.get("skill", "")
                if not skill:
                    continue
                link = coursera_search_link(skill)
                st.markdown(f"- **{skill}** — [Search Coursera courses]({link})")

        st.markdown("### 📩 Save Your Profile")
        if st.button("Save My Profile"):
            selected_skills = st.session_state.get("selected_skills", [])
            jd_scores_list = st.session_state.get("jd_scores", [])
            user_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else None
            if not user_email:
                st.error("❌ You must be logged in to save a profile.")
            else:
                profile_data = {
                    "user_email": user_email,
                    "name": st.session_state.get("active_profile"),
                    "job_title": st.session_state.get("cand_title", ""),
                    "resume_text": st.session_state.get("resume_text", ""),
                    "selected_skills": selected_skills,
                    "behavior_score": st.session_state.get("behavior_score"),
                    "reference_data": {"mock": "data"},  # TODO: wire real reference data once Step 4 persists it
                    "education": {"mock": "data"},        # TODO: wire real education data once Step 6 persists it
                    "qoh_score": st.session_state.get("qoh_score"),
                    "jd_scores": jd_scores_list,
                    "growth_roadmap": roadmap,
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    result = supabase.table("profiles").update(profile_data) \
                        .eq("user_email", user_email) \
                        .eq("name", profile_data["name"]).execute()
                    if result.data:
                        st.success("✅ Profile updated successfully!")
                    else:
                        supabase.table("profiles").insert(profile_data).execute()
                        st.success("✅ Profile created successfully!")
                    st.session_state.profile_saved = True
                except Exception as e:
                    st.error(f"❌ Error saving profile: {e}")

        if st.session_state.get("profile_saved"):
            if st.button("🏠 Home"):
                st.session_state.step = 0
                st.session_state.profile_selected = False
                st.session_state.profile_saved = False
                st.rerun()


# --- RECRUITER DASHBOARD ---
def qoh_badge_html(score):
    """Renders a QoH score as a color-coded pill badge instead of a bare number."""
    if score == "Incomplete":
        return '<span class="qoh-badge qoh-incomplete">Incomplete</span>'
    try:
        score = float(score)
    except (TypeError, ValueError):
        return '<span class="qoh-badge qoh-incomplete">—</span>'
    if score >= 80:
        css_class = "qoh-high"
    elif score >= 60:
        css_class = "qoh-mid"
    else:
        css_class = "qoh-low"
    return f'<span class="qoh-badge {css_class}">{score}</span>'


def recruiter_dashboard():
    st.markdown("""
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:1.2rem;">
            <div style="width:32px;height:32px;background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                        border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <span style="color:#FFFFFF;font-weight:800;font-size:1rem;">S</span>
            </div>
            <span style="font-size:1.15rem;font-weight:800;letter-spacing:-0.02em;
                         background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                         -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                         background-clip:text;">Skippr</span>
        </div>
    """, unsafe_allow_html=True)
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

    try:
        result = supabase.table("profiles").select("*").execute()
    except Exception as e:
        st.error(f"❌ Failed to load candidates: {e}")
        return

    rows = result.data or []
    if not rows:
        st.info("No candidate profiles have been submitted yet.")
        return

    def jd_match(row):
        scores = row.get("jd_scores") or []
        return round(sum(scores) / len(scores), 1) if scores else None

    def skill_score(row):
        skills = row.get("selected_skills") or []
        return min(len(skills) * 10, 100)

    records = []
    for row in rows:
        jd = jd_match(row)
        behavior = row.get("behavior_score")
        skill = skill_score(row)
        if jd is None or behavior is None:
            records.append({
                "Candidate": row.get("name", "Unknown"),
                "JD Match": jd if jd is not None else "—",
                "Behavior": behavior if behavior is not None else "—",
                "Skill": skill,
                "QoH Score": "Incomplete",
                "Gaps": "Missing JD match and/or behavioral survey data",
            })
            continue
        records.append({
            "Candidate": row.get("name", "Unknown"),
            "JD Match": jd,
            "Behavior": behavior,
            "Skill": skill,
            "QoH Score": round((jd * w_jd + behavior * w_beh + skill * w_skill) / (w_jd + w_beh + w_skill), 1) if (w_jd + w_beh + w_skill) else "—",
            "Gaps": "",
        })

    df = pd.DataFrame(records)
    st.subheader("📊 Candidate Comparison Table")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 AI Recommendations")
    for _, row in df.iterrows():
        score = row["QoH Score"]
        if score == "Incomplete":
            st.info(f"ℹ️ {row['Candidate']}: {row['Gaps']}")
        elif score >= 90:
            st.success(f"✅ {row['Candidate']}: Strong hire.")
        elif row["Behavior"] < 70:
            st.warning(f"⚠️ {row['Candidate']}: Weak behavioral signal.")
        elif row["Skill"] < 50:
            st.info(f"ℹ️ {row['Candidate']}: Thin skill coverage.")
        else:
            st.write(f"{row['Candidate']}: Interview-ready.")


# --- LOGIN UI ---
def login_ui():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="display:flex;flex-direction:column;align-items:center;text-align:center;
                        margin:2.5rem 0 2rem 0;">
                <div style="width:120px;height:120px;background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                            border-radius:28px;display:flex;align-items:center;justify-content:center;
                            box-shadow:0 12px 36px rgba(45,91,255,0.4);margin-bottom:1.5rem;">
                    <span style="color:#FFFFFF;font-weight:800;font-size:3.8rem;">S</span>
                </div>
                <span style="font-size:3rem;font-weight:800;letter-spacing:-0.03em;
                             background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                             background-clip:text;margin-bottom:1.2rem;">Skippr</span>
                <h1 style="font-size:2.3rem;font-weight:800;letter-spacing:-0.03em;line-height:1.15;
                           margin:0 0 1.2rem 0;color:#16181D;">
                    From Rejection to <span style="color:#2D5BFF;">Revolution</span>
                </h1>
                <p style="font-size:1.05rem;color:#6B7280;max-width:420px;margin:0;">
                    💡 I didn't get the job. I built the platform that fixes the problem.
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    with st.sidebar:
        st.markdown("""
            <div style="display:flex;align-items:center;gap:0.6rem;margin:0.2rem 0 1.5rem 0;">
                <div style="width:36px;height:36px;background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                            border-radius:9px;display:flex;align-items:center;justify-content:center;
                            box-shadow:0 3px 10px rgba(45,91,255,0.3);flex-shrink:0;">
                    <span style="color:#FFFFFF;font-weight:800;font-size:1.15rem;">S</span>
                </div>
                <span style="font-size:1.35rem;font-weight:800;letter-spacing:-0.02em;
                             background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                             background-clip:text;">Skippr</span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("""
            <p style="font-size:1.05rem;font-weight:700;color:#16181D;margin-bottom:1rem;">
                Log in or create your account
            </p>
        """, unsafe_allow_html=True)
        mode = st.radio("Choose Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.session_state.profile_selected = False
                st.success("✅ Logged in successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email.")
            except Exception as e:
                st.error(f"Signup failed: {e}")

# --- ROUTING ---
# NOTE: manual portal switch for local testing. This bypasses the
# server-side role check in auth/roles.py -- do not ship this to real
# users without bringing back get_user_role() as the actual gate.
if st.session_state.supabase_user:
    with st.sidebar:
        st.markdown("---")
        portal = st.radio("View As (testing only)", ["Candidate", "Recruiter"], key="portal_choice")

    if portal == "Recruiter":
        recruiter_dashboard()
    else:
        if not st.session_state.get("profile_selected"):
            profile_management()
        else:
            candidate_journey()
else:
    login_ui()
