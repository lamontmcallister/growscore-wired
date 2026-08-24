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
from candidates.backchannel import render_request_backchannel_ui, render_reference_response_page
from candidates.match_analytics import render_match_analytics
from ai.job_url_parser import fetch_job_posting
from marketing.pages import render_marketing_page

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
                    insert_result = supabase.table("profiles").insert(profile_data).execute()
                    st.success(f"✅ New profile '{new_name}' created successfully!")
                    st.session_state.active_profile = new_name
                    # Capture the real database id -- needed to scope backchannel
                    # references to THIS profile, not every profile under this login.
                    st.session_state.active_profile_id = insert_result.data[0]["id"] if insert_result.data else None
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
        # Capture the real database id here too, for the same reason as above.
        st.session_state.active_profile_id = profile_data.get("id")
        # Load the saved resume and active JD back into session state, so
        # Steps 1 and 8 pre-fill with what's already saved on this profile
        # instead of forcing the candidate to re-upload/re-paste every time.
        if profile_data.get("resume_text"):
            st.session_state.resume_text = profile_data["resume_text"]
        if profile_data.get("active_jd_text"):
            st.session_state._loaded_active_jd_text = profile_data["active_jd_text"]
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
                st.session_state.active_profile_id = None
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

        if st.session_state.get("resume_text") and not st.session_state.get("_resume_just_uploaded"):
            st.info("📄 A resume is already saved on this profile. Upload a new one below to replace it.")

        uploaded = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
        if uploaded:
            text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else "\n".join([p.extract_text() for p in pdfplumber.open(uploaded).pages if p.extract_text()])
            st.session_state.resume_text = text
            st.session_state._resume_just_uploaded = True

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

            # Auto-save immediately -- if the candidate never reaches the
            # final "Save My Profile" step, the resume they just uploaded
            # isn't lost. This overwrites any previously saved resume on
            # this profile, matching "persists unless updated/deleted."
            active_profile_id = st.session_state.get("active_profile_id")
            if active_profile_id:
                try:
                    save_result = supabase.table("profiles").update({"resume_text": text}).eq("id", active_profile_id).execute()
                    if save_result.data:
                        st.success("✅ Resume parsed and saved to your profile.")
                    else:
                        st.warning("Resume parsed, but the save didn't affect any row -- try reselecting your profile from the home screen.")
                except Exception as e:
                    st.warning(f"Resume parsed, but couldn't auto-save yet: {e}")
            else:
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
        st.markdown("""_This is what makes Skippr different: real people answer honest questions about working with you -- not a self-reported name and email._""")
        user_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else None
        if user_email:
            render_request_backchannel_ui(supabase, user_email, st.session_state.get("active_profile_id"))
        else:
            st.info("Log in to request a reference.")
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 4:
        st.markdown("### 📣 Step 5: Reference Summary")
        st.markdown("""_A quick recap of the references you've requested so far. You can request more anytime from Step 4._""")
        user_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else None
        if user_email:
            try:
                summary_query = supabase.table("backchannel_references").select("*").eq("candidate_email", user_email)
                if st.session_state.get("active_profile_id"):
                    summary_query = summary_query.eq("profile_id", st.session_state.active_profile_id)
                summary_result = summary_query.execute()
                summary_rows = summary_result.data or []
                responded_count = sum(1 for r in summary_rows if r.get("responded"))
                st.metric("Verified References", f"{responded_count} / {len(summary_rows)} requested")
                if responded_count == 0:
                    st.caption("ℹ️ No verified references yet -- this affects your QoH score. Go back to Step 4 to request one.")
            except Exception as e:
                st.caption(f"Couldn't load reference summary: {e}")
        else:
            st.info("Log in to see your reference summary.")
        st.button("← Skip Back", on_click=prev_step)
        st.button("Skip →", on_click=next_step)

    elif step == 5:
        st.markdown("### 🎓 Step 6: Education")
        st.markdown("""_Add education details to boost trust and completeness in your profile._""")
        edu_degree = st.text_input("Degree", key="edu_degree")
        edu_major = st.text_input("Major", key="edu_major")
        edu_institution = st.text_input("Institution", key="edu_institution")
        edu_year = st.text_input("Graduation Year", key="edu_year")
        # Real education data, stored for saving -- not hardcoded mock data.
        st.session_state.education_data = {
            "degree": edu_degree, "major": edu_major,
            "institution": edu_institution, "graduation_year": edu_year,
        }
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
        st.markdown("""_Paste the job description you're targeting, or try a job posting link. We'll show exactly what matches and what's missing -- not just a score._""")

        with st.expander("🔗 Or paste a job posting link"):
            job_url_input = st.text_input("Job posting URL")
            if st.button("Fetch Job Details") and job_url_input:
                with st.spinner("Reading the job posting..."):
                    job_data, job_error = fetch_job_posting(job_url_input)
                if job_error:
                    st.warning(f"⚠️ {job_error}")
                else:
                    st.session_state.job_url_title = job_data.get("title", "")
                    st.session_state.job_url_company = job_data.get("company", "")
                    st.session_state.job_url_url = job_data.get("url", "")
                    if job_data.get("extraction_level") == "structured":
                        # Full, real job description found -- safe to
                        # auto-fill the actual scoring field.
                        st.session_state.jd_target_text = job_data.get("description", "")
                        st.success(f"✅ Found: {job_data.get('title', '')} at {job_data.get('company', '') or 'this company'}. Description filled in below.")
                    else:
                        # Only a title/teaser snippet found -- NOT reliable
                        # enough to score against. Save title/company for
                        # record-keeping, but require the candidate to
                        # paste the real JD text themselves.
                        st.info(f"Found the posting for **{job_data.get('title', '')}**"
                                + (f" at **{job_data.get('company', '')}**" if job_data.get('company') else "")
                                + ", but couldn't pull the full description automatically. Paste it below.")

        default_jd = st.session_state.get("jd_target_text") or st.session_state.get("_loaded_active_jd_text", "")
        jd_target = st.text_area("Paste the job description you're targeting", value=default_jd, height=200)
        if st.button("Analyze Match") and jd_target and "resume_text" in st.session_state:
            with st.spinner("Analyzing your fit against this role..."):
                match_data, match_error = match_resume_to_jd(st.session_state.resume_text, jd_target)
            if match_error:
                st.error(f"⚠️ Couldn't analyze this match right now ({match_error}). Try again in a moment.")
            else:
                st.session_state.jd_target_text = jd_target
                st.session_state.jd_match_data = match_data
                st.session_state.jd_scores = [match_data.get("score", 0)]
                # Save every analysis to job_matches so candidates build real
                # history across every role they check themselves against,
                # instead of only ever seeing their most recent result.
                user_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else None
                if user_email:
                    try:
                        supabase.table("job_matches").insert({
                            "user_email": user_email,
                            "profile_id": st.session_state.get("active_profile_id"),
                            "jd_text": jd_target,
                            "score": match_data.get("score", 0),
                            "matched_skills": match_data.get("matched_skills", []),
                            "missing_skills": match_data.get("missing_skills", []),
                            "job_title": st.session_state.get("job_url_title", ""),
                            "company_name": st.session_state.get("job_url_company", ""),
                            "job_url": st.session_state.get("job_url_url", ""),
                        }).execute()
                    except Exception as e:
                        st.caption(f"⚠️ Match shown above, but couldn't save to your history: {e}")
                # Also save as this profile's CURRENT active JD -- separate
                # from the job_matches history log above. Persists unless
                # the candidate pastes a new one (which overwrites it) or
                # deletes the profile.
                active_profile_id = st.session_state.get("active_profile_id")
                if active_profile_id:
                    try:
                        supabase.table("profiles").update({"active_jd_text": jd_target}).eq("id", active_profile_id).execute()
                    except Exception as e:
                        st.caption(f"⚠️ Match shown above, but couldn't save as your active JD: {e}")

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
        # Real reference score: based on how many references have actually
        # RESPONDED via the backchannel system (verified by a real person),
        # not how many names/emails the candidate typed in.
        qoh_user_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else None
        reference_count = 0
        if qoh_user_email:
            try:
                ref_query = supabase.table("backchannel_references").select("responded").eq("candidate_email", qoh_user_email).eq("responded", True)
                if st.session_state.get("active_profile_id"):
                    ref_query = ref_query.eq("profile_id", st.session_state.active_profile_id)
                ref_result = ref_query.execute()
                reference_count = len(ref_result.data or [])
            except Exception as e:
                st.caption(f"Couldn't load verified reference count: {e}")
        ref_score = min(reference_count * 45, 100)
        if reference_count == 0:
            st.caption("ℹ️ No verified references yet -- this affects your QoH score. Request one in Step 4.")
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

        st.markdown("---")
        render_match_analytics(supabase, st.session_state.get("active_profile_id"))

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
                # Pull real, verified reference data at save time -- only
                # references that actually responded, not self-entered
                # names. This replaces the old session-state reference_data,
                # which no longer gets set now that Step 4 uses the real
                # backchannel system instead of a self-reported form.
                verified_references = []
                try:
                    ref_save_query = supabase.table("backchannel_references").select(
                        "reference_name, relationship, would_recommend, strengths, work_style_notes, fit_notes"
                    ).eq("candidate_email", user_email).eq("responded", True)
                    if st.session_state.get("active_profile_id"):
                        ref_save_query = ref_save_query.eq("profile_id", st.session_state.active_profile_id)
                    ref_save_result = ref_save_query.execute()
                    verified_references = ref_save_result.data or []
                except Exception as e:
                    st.caption(f"⚠️ Couldn't load verified references for saving: {e}")

                profile_data = {
                    "user_email": user_email,
                    "name": st.session_state.get("active_profile"),
                    "job_title": st.session_state.get("cand_title", ""),
                    "resume_text": st.session_state.get("resume_text", ""),
                    "selected_skills": selected_skills,
                    "behavior_score": st.session_state.get("behavior_score"),
                    "reference_data": verified_references,
                    "education": st.session_state.get("education_data", {}),
                    "qoh_score": st.session_state.get("qoh_score"),
                    "jd_scores": jd_scores_list,
                    "growth_roadmap": roadmap,
                    "timestamp": datetime.utcnow().isoformat()
                }
                active_profile_id = st.session_state.get("active_profile_id")
                if not active_profile_id:
                    st.error("❌ Couldn't find this profile's database record. Try reselecting your profile from the home screen before saving.")
                else:
                    try:
                        # Match by the real database id, not by name -- name
                        # matching is fragile (whitespace, exact-string) and
                        # was the root cause of duplicate profile rows being
                        # silently created when an update matched nothing.
                        result = supabase.table("profiles").update(profile_data) \
                            .eq("id", active_profile_id).execute()
                        if result.data:
                            st.success("✅ Profile updated successfully!")
                        else:
                            st.error("⚠️ Save didn't affect any row. This profile may have been deleted -- try reselecting it from the home screen.")
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
    st.subheader("✅ Candidate Decisions")
    st.caption("Mark each candidate's status. These decisions are saved and will inform future scoring calibration.")

    decision_options = ["No decision yet", "Strong Hire", "Maybe", "Pass"]
    recruiter_email = st.session_state.supabase_user.email if st.session_state.get("supabase_user") else "unknown"

    for row in rows:
        candidate_name = row.get("name", "Unknown")
        current_decision = row.get("recruiter_decision") or "No decision yet"
        with st.expander(f"{candidate_name} — {current_decision}"):
            new_decision = st.selectbox(
                "Decision",
                decision_options,
                index=decision_options.index(current_decision) if current_decision in decision_options else 0,
                key=f"decision_{row.get('id')}",
            )
            if st.button("Save Decision", key=f"save_decision_{row.get('id')}"):
                if new_decision == "No decision yet":
                    st.warning("Select an actual decision before saving.")
                else:
                    try:
                        supabase.table("profiles").update({
                            "recruiter_decision": new_decision,
                            "decision_made_by": recruiter_email,
                            "decision_made_at": datetime.utcnow().isoformat(),
                        }).eq("id", row.get("id")).execute()
                        st.success(f"Saved: {candidate_name} → {new_decision}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to save decision: {e}")

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
    st.markdown("""
        <div style="width:100%;height:280px;border-radius:20px;overflow:hidden;
                    position:relative;margin-bottom:2rem;">
            <img src="https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=2070&auto=format&fit=crop"
                 style="width:100%;height:100%;object-fit:cover;position:absolute;top:0;left:0;">
            <div style="position:absolute;top:0;left:0;width:100%;height:100%;
                        background:linear-gradient(135deg, rgba(45,91,255,0.75), rgba(0,194,168,0.55));">
            </div>
            <div style="position:relative;height:100%;display:flex;align-items:center;
                        justify-content:center;text-align:center;padding:1rem;">
                <span style="color:#FFFFFF;font-size:1.4rem;font-weight:700;
                             text-shadow:0 2px 12px rgba(0,0,0,0.25);max-width:600px;">
                    Real people. Verified references. Hired with confidence.
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="background:linear-gradient(180deg, rgba(45,91,255,0.05), rgba(0,194,168,0.03));
                        border-radius:20px;padding:2.5rem 2rem;margin:0.5rem 0 2rem 0;">
                <div style="display:flex;flex-direction:column;align-items:center;text-align:center;">
                    <h1 style="font-size:2.3rem;font-weight:800;letter-spacing:-0.03em;line-height:1.15;
                               margin:0 0 1rem 0;color:#16181D;">
                        From Rejection to <span style="color:#2D5BFF;">Revolution</span>
                    </h1>
                    <p style="font-size:1.05rem;color:#6B7280;max-width:420px;margin:0 0 2rem 0;">
                        💡 I didn't get the job. I built the platform that fixes the problem.
                    </p>
                    <div style="display:flex;gap:2rem;flex-wrap:wrap;justify-content:center;width:100%;">
                        <div style="flex:1;min-width:140px;text-align:center;">
                            <div style="font-size:1.8rem;margin-bottom:0.4rem;">🤝</div>
                            <div style="font-weight:700;color:#16181D;font-size:0.95rem;">Verified References</div>
                            <div style="color:#6B7280;font-size:0.85rem;">Real people, not self-reported claims</div>
                        </div>
                        <div style="flex:1;min-width:140px;text-align:center;">
                            <div style="font-size:1.8rem;margin-bottom:0.4rem;">🎯</div>
                            <div style="font-weight:700;color:#16181D;font-size:0.95rem;">Evidence-Based Matching</div>
                            <div style="color:#6B7280;font-size:0.85rem;">Scores explained, not a black box</div>
                        </div>
                        <div style="flex:1;min-width:140px;text-align:center;">
                            <div style="font-size:1.8rem;margin-bottom:0.4rem;">🚀</div>
                            <div style="font-weight:700;color:#16181D;font-size:0.95rem;">Real Career Roadmap</div>
                            <div style="color:#6B7280;font-size:0.85rem;">Targeted at your actual gaps</div>
                        </div>
                    </div>
                </div>
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
# Public, unauthenticated route: a reference clicking their tokenized link
# lands here directly, with no login required. This must be checked before
# any auth-gated routing below.
query_params = st.query_params
if "ref" in query_params:
    render_reference_response_page(query_params["ref"])
    st.stop()

# Public marketing site: /?mkt=home, ?mkt=candidates, ?mkt=recruiters, ?mkt=about
# ?mkt=login is a special case: it's the CTA target from marketing pages,
# and just falls through to the normal login/app routing below rather than
# rendering a marketing page.
if "mkt" in query_params and query_params["mkt"] != "login":
    render_marketing_page(query_params["mkt"])
    st.stop()

# Default landing: a logged-out visitor hitting the bare root URL (no query
# params) sees the marketing Home page first, not the login form directly.
# Logged-in users skip straight past this into the real app -- they
# shouldn't be shown marketing content every time they return.
if not st.session_state.supabase_user and not query_params:
    render_marketing_page("home")
    st.stop()

# Real server-side role gate: role comes from Supabase auth user_metadata,
# verified via get_user_role(), NOT a client-side toggle a visitor could
# flip themselves. To grant recruiter access to an account, set
# user_metadata.role = "recruiter" for that user in Supabase.
if st.session_state.supabase_user:
    user_role = get_user_role(st.session_state.supabase_user)

    if user_role == "recruiter":
        recruiter_dashboard()
    else:
        if not st.session_state.get("profile_selected"):
            profile_management()
        else:
            candidate_journey()
else:
    login_ui()
