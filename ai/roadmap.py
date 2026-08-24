import streamlit as st
from ai.resume import call_openai_json
from ai.learning_resources import coursera_search_link


def generate_roadmap(resume_text: str, missing_skills: list):
    """
    Generates a structured growth roadmap. If missing_skills is provided,
    the roadmap targets those specific gaps (used for a specific job
    match). If empty, generates a general roadmap. Every phase is always
    a structured {action, gap_addressed} object -- never a bare string --
    so display code never has to guess at the shape.
    """
    if missing_skills:
        gap_lines = "\n".join(
            f"- {item.get('skill', '')}: {item.get('why_it_matters', '')}"
            for item in missing_skills if isinstance(item, dict)
        )
        prompt = (
            f"Given this resume:\n{resume_text}\n\n"
            f"This candidate is targeting a specific role and has these skill gaps:\n{gap_lines}\n\n"
            "Create a career roadmap specifically focused on closing THESE gaps, in priority order.\n\n"
            "Respond as JSON where EVERY phase is an object with an 'action' string and a "
            "'gap_addressed' list of the specific gap name(s) from above that phase targets:\n"
            '{"30_day": {"action": "...", "gap_addressed": ["..."]}, '
            '"60_day": {"action": "...", "gap_addressed": ["..."]}, '
            '"90_day": {"action": "...", "gap_addressed": ["..."]}, '
            '"6_month": {"action": "...", "gap_addressed": ["..."]}, '
            '"1_year": {"action": "...", "gap_addressed": ["..."]}}'
        )
    else:
        prompt = (
            f"Given this resume:\n{resume_text}\n\n"
            "Create a career roadmap. Respond as JSON where EVERY phase is an object with an "
            "'action' string and an empty 'gap_addressed' list (no specific gaps to target yet):\n"
            '{"30_day": {"action": "...", "gap_addressed": []}, '
            '"60_day": {"action": "...", "gap_addressed": []}, '
            '"90_day": {"action": "...", "gap_addressed": []}, '
            '"6_month": {"action": "...", "gap_addressed": []}, '
            '"1_year": {"action": "...", "gap_addressed": []}}'
        )

    return call_openai_json(prompt, temperature=0.7)


def render_roadmap(roadmap: dict, missing_skills: list = None):
    """
    Renders a generated roadmap as styled timeline cards with gap-addressed
    pills, followed by real Coursera search links for each missing skill.
    Shared by Step 10 and the per-match analytics dropdowns so both look
    identical. Handles a plain string phase gracefully (in case older saved
    data isn't in the structured shape) instead of printing a raw dict.
    """
    missing_skills = missing_skills or []
    phases = [
        ("30_day", "30 Days", "🚀"),
        ("60_day", "60 Days", "📈"),
        ("90_day", "90 Days", "🎯"),
        ("6_month", "6 Months", "🏔️"),
        ("1_year", "1 Year", "🏆"),
    ]
    for key, label, icon in phases:
        phase_data = roadmap.get(key, {})
        if isinstance(phase_data, dict):
            action_text = phase_data.get("action", "")
            gaps = phase_data.get("gap_addressed", []) or []
        else:
            action_text = str(phase_data)
            gaps = []

        gap_pills = "".join(
            f'<span style="display:inline-block;background:rgba(45,91,255,0.1);color:#2D5BFF;'
            f'font-size:0.75rem;font-weight:600;padding:0.2rem 0.6rem;border-radius:999px;'
            f'margin-right:0.4rem;">{g}</span>'
            for g in gaps
        )
        st.markdown(f"""
            <div style="border:1px solid #E4E6EA;border-radius:12px;padding:1.1rem 1.4rem;
                        margin-bottom:0.8rem;background:#FFFFFF;">
                <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">
                    <span style="font-size:1.3rem;">{icon}</span>
                    <span style="font-weight:700;color:#16181D;">{label}</span>
                </div>
                <p style="color:#3A3F47;font-size:0.95rem;margin:0 0 0.5rem 0;">{action_text}</p>
                {gap_pills}
            </div>
        """, unsafe_allow_html=True)

    if missing_skills:
        st.markdown("**📚 Recommended Learning**")
        st.caption("Real search results on Coursera for each gap -- not AI-guessed course names.")
        for item in missing_skills:
            if not isinstance(item, dict):
                continue
            skill = item.get("skill", "")
            if not skill:
                continue
            link = coursera_search_link(skill)
            st.markdown(f"- **{skill}** — [Search Coursera courses]({link})")
