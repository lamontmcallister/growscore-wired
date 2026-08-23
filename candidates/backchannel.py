import streamlit as st
from datetime import datetime
from db.client import get_fresh_anon_client


def render_request_backchannel_ui(supabase, candidate_email, profile_id=None):
    """
    Lets a candidate request a backchannel reference: a real person answers
    fit-focused questions about the candidate via a tokenized link, with no
    Skippr account required. This is the mutual-fit signal that
    resume-only AI matching can't produce.
    """
    st.markdown("#### 🔗 Request a Backchannel Reference")
    st.caption("This person will get a private link to answer a few questions about working with you. No account needed for them.")

    with st.form("backchannel_request_form", clear_on_submit=True):
        ref_name = st.text_input("Their name")
        ref_email = st.text_input("Their email")
        relationship = st.selectbox(
            "Relationship",
            ["Former Manager", "Peer / Colleague", "Direct Report", "Client", "Other"],
        )
        submitted = st.form_submit_button("Generate Reference Link")

    if submitted:
        if not ref_name or not ref_email:
            st.warning("Enter both a name and email before generating a link.")
        else:
            try:
                result = supabase.table("backchannel_references").insert({
                    "candidate_email": candidate_email,
                    "profile_id": profile_id,
                    "reference_name": ref_name,
                    "reference_email": ref_email,
                    "relationship": relationship,
                }).execute()
                token = result.data[0]["response_token"]
                base_url = st.secrets.get("app", {}).get("base_url", "")
                link = f"{base_url}/?ref={token}" if base_url else f"?ref={token}"
                st.success(f"Link generated for {ref_name}. Copy and send it to them directly (email sending isn't wired up yet):")
                st.code(link, language=None)
                if base_url:
                    st.markdown(f"[Open this link to test it]({link})")
            except Exception as e:
                st.error(f"❌ Couldn't create the reference request: {e}")

    _render_existing_requests(supabase, candidate_email, profile_id)


def _render_existing_requests(supabase, candidate_email, profile_id=None):
    try:
        query = supabase.table("backchannel_references").select("*").eq("candidate_email", candidate_email)
        # Scope to this specific profile when we have an id -- otherwise
        # (e.g. older references saved before this fix) fall back to
        # showing all references under this login, rather than hiding them.
        if profile_id:
            query = query.eq("profile_id", profile_id)
        result = query.execute()
    except Exception as e:
        st.caption(f"Couldn't load your reference requests: {e}")
        return

    rows = result.data or []
    if not rows:
        return

    st.markdown("#### 📋 Your Backchannel References")
    for row in rows:
        status = "✅ Responded" if row.get("responded") else "⏳ Waiting on response"
        with st.expander(f"{row.get('reference_name')} ({row.get('relationship')}) — {status}"):
            if row.get("responded"):
                st.write(f"**Would recommend:** {'Yes' if row.get('would_recommend') else 'No'}")
                st.write(f"**Strengths:** {row.get('strengths', '')}")
                st.write(f"**Work style notes:** {row.get('work_style_notes', '')}")
                st.write(f"**Fit notes:** {row.get('fit_notes', '')}")
            else:
                base_url = st.secrets.get("app", {}).get("base_url", "")
                pending_link = f"{base_url}/?ref={row.get('response_token')}" if base_url else f"?ref={row.get('response_token')}"
                st.code(pending_link, language=None)


def render_reference_response_page(token):
    """
    Public, unauthenticated page a reference lands on via their tokenized
    link. No Skippr login required -- the token itself is the access
    credential, matching the anon RLS policies on backchannel_references.

    Uses get_fresh_anon_client() rather than the shared cached client: the
    cached client is reused across every user session on the server, so if
    any user happens to be logged in elsewhere, this page could otherwise
    inherit their auth token instead of hitting RLS as a true anonymous
    'anon' request.
    """
    st.markdown("### 🤝 You've been asked to be a reference")
    client = get_fresh_anon_client()

    try:
        result = client.table("backchannel_references").select("*").eq("response_token", token).execute()
    except Exception as e:
        st.error(f"❌ Couldn't load this reference request: {e}")
        return

    rows = result.data or []
    if not rows:
        st.error("This link isn't valid. Double check it was copied correctly.")
        return

    record = rows[0]

    if record.get("responded"):
        st.success("You've already submitted your response for this reference. Thank you!")
        return

    st.write(f"**{record.get('candidate_email')}** listed you as a **{record.get('relationship')}** and would like your honest input.")
    st.caption("Your response is shared with the candidate and the hiring team reviewing them -- it is not shared publicly.")

    with st.form("backchannel_response_form"):
        would_recommend = st.radio("Would you recommend working with them?", ["Yes", "No"])
        strengths = st.text_area("What are their biggest strengths?")
        work_style_notes = st.text_area("What's their work style like? (e.g. pace, structure, communication)")
        fit_notes = st.text_area("Any advice for a team considering hiring them?")
        submitted = st.form_submit_button("Submit Response")

    if submitted:
        try:
            update_result = client.table("backchannel_references").update({
                "responded": True,
                "would_recommend": would_recommend == "Yes",
                "strengths": strengths,
                "work_style_notes": work_style_notes,
                "fit_notes": fit_notes,
                "responded_at": datetime.utcnow().isoformat(),
            }).eq("response_token", token).execute()
            if update_result.data:
                st.success("✅ Thank you! Your response has been recorded.")
            else:
                st.error("⚠️ Your response wasn't saved (no rows were updated). This is likely a permissions issue -- please let the candidate know this link didn't work.")
        except Exception as e:
            st.error(f"❌ Couldn't submit your response: {e}")
