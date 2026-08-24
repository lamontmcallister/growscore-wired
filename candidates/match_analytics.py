import streamlit as st


def render_match_analytics(supabase, profile_id):
    """
    Shows every job description this profile has been analyzed against,
    sorted by score, with the strongest match highlighted. All data comes
    from job_matches rows already written by Step 8's "Analyze Match" --
    this is a read/display layer, not a new scoring pipeline.
    """
    st.markdown("### 📊 Your Match Analytics")
    st.markdown("""_Every role you've checked yourself against, in one place. Revisit your strongest matches anytime._""")

    if not profile_id:
        st.info("Select or create a profile to see your match history.")
        return

    try:
        result = supabase.table("job_matches").select("*").eq("profile_id", profile_id).order("score", desc=True).execute()
    except Exception as e:
        st.error(f"❌ Couldn't load your match history: {e}")
        return

    matches = result.data or []
    if not matches:
        st.info("No job matches yet. Go to Step 8 and analyze a job description to start building your history.")
        return

    scores = [m.get("score", 0) for m in matches]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    best_match = matches[0]  # already sorted desc by score

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Roles Analyzed", len(matches))
    with col2:
        st.metric("Average Match Score", f"{avg_score}%")
    with col3:
        st.metric("Best Match Score", f"{best_match.get('score', 0)}%")

    st.markdown("---")
    st.markdown("#### 🔥 Your Hottest Prospect")
    _render_match_card(best_match, highlight=True)

    if len(matches) > 1:
        st.markdown("---")
        st.markdown("#### All Matches")
        for match in matches[1:]:
            _render_match_card(match, highlight=False)


def _render_match_card(match, highlight: bool):
    score = match.get("score", 0)
    job_title = match.get("job_title") or ""
    company_name = match.get("company_name") or ""
    job_url = match.get("job_url") or ""

    jd_preview = (match.get("jd_text") or "")[:120].strip()
    if len(match.get("jd_text") or "") > 120:
        jd_preview += "..."

    border_color = "#2D5BFF" if highlight else "#E4E6EA"
    bg_color = "rgba(45,91,255,0.04)" if highlight else "#FFFFFF"

    # Real job title/company, when we have them from a parsed URL --
    # otherwise fall back to the plain JD text preview, same as before.
    if job_title:
        heading = job_title + (f" — {company_name}" if company_name else "")
    else:
        heading = jd_preview

    with st.container():
        st.markdown(f"""
            <div style="border:1px solid {border_color};border-radius:12px;padding:1.25rem 1.5rem;
                        background:{bg_color};margin-bottom:1rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                    <span style="font-weight:700;font-size:1.4rem;color:#16181D;">{score}%</span>
                </div>
                <p style="color:#16181D;font-size:0.95rem;font-weight:600;margin:0 0 0.3rem 0;">{heading}</p>
            </div>
        """, unsafe_allow_html=True)
        if job_url:
            st.markdown(f"[🔗 View / apply to this role]({job_url})")

        matched = match.get("matched_skills") or []
        missing = match.get("missing_skills") or []
        if matched or missing:
            with st.expander("View match details"):
                if matched:
                    st.markdown("**✅ Matched skills**")
                    for item in matched:
                        skill = item.get("skill", "") if isinstance(item, dict) else item
                        st.markdown(f"- {skill}")
                if missing:
                    st.markdown("**🔍 Skills to develop**")
                    for item in missing:
                        skill = item.get("skill", "") if isinstance(item, dict) else item
                        st.markdown(f"- {skill}")
