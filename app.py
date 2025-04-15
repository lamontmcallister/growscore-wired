
import streamlit as st

st.set_page_config(page_title="Skippr", layout="wide")

# --- SESSION STATE SETUP ---
if "show_login" not in st.session_state:
    st.session_state.show_login = False

# --- LANDING PAGE ---
if not st.session_state.show_login:
    st.markdown("""
        <div style='text-align: center; padding-top: 4rem;'>
            <h1 style='font-size: 3rem; color: #222;'>Skippr</h1>
            <h3 style='color: #555;'>Predictive Hiring. Verified Potential. Human-first AI.</h3>
            <p style='font-size: 18px; color: #666; max-width: 700px; margin: 2rem auto;'>
                Skippr helps job seekers showcase verified qualifications and lets hiring teams focus on real signals—not just resumes.
                Built with AI, Supabase, and Streamlit.
            </p>
            <form action="" method="post">
                <button type="submit" style='margin-top: 2rem; font-size: 18px;' onclick="window.location.reload()">🚀 Get Started</button>
            </form>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🚀 Features")
    st.markdown("#### 👤 Candidate Journey")
    st.markdown("""
- ✅ Resume upload + GPT-powered parsing  
- ✅ Contact info + skill extraction  
- ✅ Semantic job description matching (with radar chart)  
- ✅ Reference + backchannel input  
- ✅ Education section  
- ✅ Growth roadmap with personalized recommendations  
- ✅ Final verification summary and credibility score  
    """)

    st.markdown("#### 🧑‍💼 Recruiter Dashboard")
    st.markdown("""
- 🎯 Quality of Hire (QoH) scoring engine  
- 🎚 Adjustable input weights (JD match, behavior, references, skills)  
- 🧠 AI-powered candidate recommendations  
- 📊 Side-by-side candidate comparison table  
- 🔍 Skill gap analysis and performance predictions  
    """)

    if st.button("🚀 Get Started", key="start_button"):
        st.session_state.show_login = True

# --- LOGIN PAGE ---
else:
    st.markdown("### 👋 Welcome back to Skippr")
    st.markdown("Let's get you growing again. Log in to continue.")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login"):
        st.success("🚀 Login successful (placeholder logic)")
        # Add real auth logic here

    st.markdown("Don't have an account? [Sign up](#)", unsafe_allow_html=True)
