
import streamlit as st

st.set_page_config(page_title="Skippr", layout="wide")

# --- SESSION STATE SETUP ---
if "show_login" not in st.session_state:
    st.session_state.show_login = False

# --- STYLES ---
st.markdown("""
    <style>
        .centered {
            text-align: center;
            padding-top: 4rem;
        }
        .mission-text {
            font-size: 18px;
            color: #444;
            max-width: 800px;
            margin: 2rem auto;
            text-align: center;
        }
        .hero-title {
            font-size: 3rem;
            color: #1A1A1A;
        }
        .subtitle {
            font-size: 1.25rem;
            color: #555;
            margin-top: 0.5rem;
        }
        .start-button {
            display: flex;
            justify-content: center;
            margin-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- LANDING PAGE ---
if not st.session_state.show_login:
    st.markdown("""
        <div class='centered'>
            <div class='hero-title'>Skippr</div>
            <div class='subtitle'>Predictive Hiring. Verified Potential. Human-first AI.</div>
            <div class='mission-text'>
                Skippr empowers job seekers to prove their readiness and value — while helping hiring teams focus on 
                verified skills, authentic growth, and predictive potential. We combine AI-driven insights with human-centered 
                design to fix the broken hiring process, from resume to results.
                <br><br>
                Built with AI, Supabase, and Streamlit.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Single clean "Get Started" button
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

    st.markdown("Don't have an account? [Sign up](#)", unsafe_allow_html=True)
