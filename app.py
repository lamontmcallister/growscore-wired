def login_ui():
    st.markdown("##")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 💬 Mission Statement")
        st.markdown("""
        <div style='text-align: center; font-size: 20px; font-weight: 500; line-height: 1.5;'>
            <em>From Rejection to Revolution.</em><br>
            Skippr exists to restore dignity in hiring—<br>
            empowering talent with data, coaching, and visibility,<br>
            while giving recruiters the signal they’ve always needed:<br>
            <strong>Verified Quality of Hire</strong>, before the first interview.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    with st.sidebar:
        st.header("🔐 Log In or Create Account")
        mode = st.radio("Choose Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Login" and st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.supabase_user = res.user
                st.session_state.supabase_session = res.session
                st.success("✅ Logged in successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

        elif mode == "Sign Up" and st.button("Register"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("✅ Account created! Check your email for verification.")
            except Exception as e:
                st.error(f"Signup failed: {e}")
