
import streamlit as st
from config import SKILLS_POOL, BEHAVIOR_QUESTIONS, BEHAVIOR_OPTIONS
from db_utils import get_profiles, save_profile, delete_profile
from utils import extract_skills_from_resume, match_resume_to_jds
import pdfplumber
import openai

st.set_page_config(page_title="Skippr", layout="wide")

# Dummy Supabase user for testing
if "supabase_user" not in st.session_state:
    st.session_state.supabase_user = type("User", (), {"id": "user-1234"})

user_id = st.session_state.supabase_user.id

# --- Load and Manage Profiles ---
st.title("👤 Candidate Journey - Multi-Profile Enabled")

profiles = get_profiles(user_id)

if profiles:
    selected_profile = st.selectbox("Select Existing Profile", [p["profile_name"] for p in profiles])
    if st.button("Load Profile"):
        profile_data = next(p["data"] for p in profiles if p["profile_name"] == selected_profile)
        st.session_state.active_profile_data = profile_data
        st.session_state.profile_name = selected_profile
        st.session_state.step = profile_data.get("step", 0)
        st.success(f"Loaded profile: {selected_profile}")
else:
    st.info("No profiles yet. Create one below!")

delete_choice = st.selectbox("Delete Profile", [p["profile_name"] for p in profiles]) if profiles else None
if delete_choice and st.button("Delete Selected Profile"):
    profile_id = next(p["id"] for p in profiles if p["profile_name"] == delete_choice)
    delete_profile(profile_id)
    st.success(f"Deleted profile: {delete_choice}")
    st.experimental_rerun()

st.markdown("---")

# --- Create or Continue Profile ---
new_profile_name = st.text_input("New Profile Name")
if new_profile_name and st.button("Start New Profile"):
    st.session_state.profile_name = new_profile_name
    st.session_state.active_profile_data = {}
    st.session_state.step = 0
    save_profile(user_id, new_profile_name, {"step": 0})
    st.success(f"Profile '{new_profile_name}' created!")
    st.experimental_rerun()

# --- Candidate Journey Steps ---
if "profile_name" in st.session_state:
    st.header(f"🚀 Journey: {st.session_state.profile_name}")
    step = st.session_state.get("step", 0)

    def save_current_step_data(extra_data={}):
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

    # --- Step 0: Resume Upload + Contact Info ---
    if step == 0:
        st.subheader("Step 1: Contact Info + Resume")
        name = st.text_input("Full Name", value=st.session_state.active_profile_data.get("name", ""))
        email = st.text_input("Email", value=st.session_state.active_profile_data.get("email", ""))
        title = st.text_input("Job Title", value=st.session_state.active_profile_data.get("title", ""))
        uploaded = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

        if uploaded:
            with pdfplumber.open(uploaded) as pdf:
                resume_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                skills = extract_skills_from_resume(resume_text)
                st.session_state.resume_text = resume_text
                st.session_state.resume_skills = skills
                st.success("Resume parsed!")

        if st.button("Next"):
            save_current_step_data({"name": name, "email": email, "title": title, "resume_text": st.session_state.get("resume_text", ""), "resume_skills": st.session_state.get("resume_skills", [])})
            next_step()

    # --- Step 1: Skills ---
    elif step == 1:
        st.subheader("Step 2: Skills")
        selected_skills = st.multiselect("Select Your Skills", SKILLS_POOL, default=st.session_state.active_profile_data.get("skills", st.session_state.get("resume_skills", [])))
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({"skills": selected_skills})
            next_step()

    # --- Step 2: Behavioral Survey ---
    elif step == 2:
        st.subheader("Step 3: Behavioral Survey")
        score_total = 0
        score_map = {opt: i + 1 for i, opt in enumerate(BEHAVIOR_OPTIONS)}
        for i, question in enumerate(BEHAVIOR_QUESTIONS):
            response = st.radio(question, BEHAVIOR_OPTIONS, index=2, key=f"behavior_{i}")
            score_total += score_map[response]
        behavior_score = round((score_total / (len(BEHAVIOR_QUESTIONS) * 5)) * 100, 1)
        st.session_state.behavior_score = behavior_score
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({"behavior_score": behavior_score})
            next_step()

    # --- Step 3: References Collection ---
    elif step == 3:
        st.subheader("Step 4: References Collection")
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
                ]
            }
            save_current_step_data(refs)
            next_step()
    # --- Step 4: Backchannel Feedback ---
    elif step == 4:
        st.subheader("Step 5: Backchannel Feedback")
        back_name = st.text_input("Colleague's Name")
        back_email = st.text_input("Colleague's Email")
        back_message = st.text_area("Message or Topic for Feedback")
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({
                "backchannel_name": back_name,
                "backchannel_email": back_email,
                "backchannel_message": back_message
            })
            next_step()

    # --- Step 5: Education ---
    elif step == 5:
        st.subheader("Step 6: Education")
        degree = st.text_input("Degree")
        major = st.text_input("Major")
        institution = st.text_input("Institution")
        grad_year = st.text_input("Graduation Year")
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({
                "education": {
                    "degree": degree,
                    "major": major,
                    "institution": institution,
                    "grad_year": grad_year
                }
            })
            next_step()

    # --- Step 6: HR Check ---
    elif step == 6:
        st.subheader("Step 7: HR Check")
        hr_company = st.text_input("Company")
        hr_manager = st.text_input("Manager")
        hr_email = st.text_input("HR Email")
        authorize = st.checkbox("I authorize verification")
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            save_current_step_data({
                "hr_check": {
                    "company": hr_company,
                    "manager": hr_manager,
                    "hr_email": hr_email,
                    "authorized": authorize
                }
            })
            next_step()

    # --- Step 7: Job Matching ---
    elif step == 7:
        st.subheader("Step 8: Job Matching")
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

    # --- Step 8: QoH Score ---
    elif step == 8:
        st.subheader("Step 9: Quality of Hire Score")
        jd_scores = st.session_state.active_profile_data.get("jd_scores", [75, 80])
        skill_count = len(st.session_state.active_profile_data.get("skills", []))
        behavior = st.session_state.active_profile_data.get("behavior_score", 50)
        ref_score = 90
        avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
        skills_score = skill_count * 5
        qoh = round((skills_score + ref_score + behavior + avg_jd) / 4, 1)
        st.metric("📈 QoH Score", f"{qoh}/100")
        save_current_step_data({"qoh": qoh, "skills_score": skills_score, "avg_jd": avg_jd, "ref_score": ref_score})
        if st.button("Back"):
            prev_step()
        if st.button("Next"):
            next_step()

    # --- Step 9: Growth Roadmap ---
    elif step == 9:
        st.subheader("Step 10: Growth Roadmap")
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
            st.success("Profile completed and saved!")

# --- Recruiter Dashboard ---
st.markdown("---")
st.header("💼 Recruiter Dashboard")

df = []
for profile in get_profiles(user_id):
    data = profile["data"]
    df.append({
        "Candidate": data.get("name", ""),
        "QoH Score": data.get("qoh", 0),
        "Skills": len(data.get("skills", [])),
        "JD Match": data.get("avg_jd", 0),
        "Behavior": data.get("behavior_score", 0),
        "References": data.get("ref_score", 0),
        "Verified": "✅" if data.get("hr_check", {}).get("authorized", False) else "❌"
    })

if df:
    st.dataframe(df, use_container_width=True)
    top_candidates = [row for row in df if row["QoH Score"] >= 85]
    st.subheader("🔍 Top Candidates")
    for cand in top_candidates:
        st.success(f"{cand['Candidate']} - QoH: {cand['QoH Score']}")
else:
    st.info("No candidates available.")
