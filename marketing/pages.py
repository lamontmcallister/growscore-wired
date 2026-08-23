import streamlit as st

# Real, free-tier Unsplash photos already verified tonight -- reused here
# rather than guessing at new photo URLs.
HERO_IMAGE = "https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=2070&auto=format&fit=crop"
CANDIDATE_IMAGE = "https://images.unsplash.com/photo-1600250395178-40fe752e5189?q=80&w=2831&auto=format&fit=crop"
RECRUITER_IMAGE = "https://images.unsplash.com/photo-1591871107448-22bc32cc37b8?w=1200&auto=format&fit=crop&q=80"


def _inject_marketing_css():
    st.markdown("""
        <style>
            .stApp {
                background: #0B0B0F !important;
            }
            [data-testid="stSidebar"] {
                display: none;
            }
            .mkt-nav {
                display: flex; align-items: center; justify-content: space-between;
                padding: 1.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);
                margin-bottom: 3rem;
            }
            .mkt-logo { font-size: 1.4rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em; }
            .mkt-links a {
                color: rgba(255,255,255,0.75); text-decoration: none; margin-left: 2rem;
                font-size: 0.95rem; font-weight: 500;
            }
            .mkt-links a:hover { color: #2D5BFF; }
            .mkt-h1 { color: #FFFFFF !important; font-size: 3rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; }
            /* The main app's global CSS forces h1/h2/h3 to a dark near-black
            color with !important -- that wins over any non-!important rule
            here, since both target the same <h1> tag. Every heading-level
            element on these dark marketing pages needs !important too, or
            text washes out invisibly against the dark background. */
            .mkt-section-title { color: #FFFFFF !important; }
            .mkt-card-title { color: #FFFFFF !important; }
            .mkt-logo { color: #FFFFFF !important; }
            .mkt-eyebrow { color: #4C7FFF; font-size: 1.15rem; line-height: 1.6; font-weight: 500; }
            .mkt-body { color: rgba(255,255,255,0.65); font-size: 1.05rem; line-height: 1.7; }
            .mkt-section-title { color: #FFFFFF; font-size: 2rem; font-weight: 800; margin-bottom: 2rem; }
            .mkt-card-title { color: #FFFFFF; font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem; }
            .mkt-cta {
                display: inline-block; background: linear-gradient(135deg,#2D5BFF,#00C2A8); color: #FFFFFF !important;
                padding: 0.8rem 1.8rem; border-radius: 8px; font-weight: 700;
                text-decoration: none; margin-top: 1.5rem;
            }
            .mkt-cta:hover { filter: brightness(1.1); }
            .mkt-footer {
                border-top: 1px solid rgba(255,255,255,0.1); margin-top: 4rem;
                padding-top: 2rem; color: rgba(255,255,255,0.45); font-size: 0.9rem;
            }
            /* Auto-scrolling pill strip, pauses on hover -- same technique
            as a logo conveyor belt, built from real Skippr feature pills
            rather than customer logos we don't have yet. */
            .mkt-marquee-outer { overflow: hidden; width: 100%; }
            .mkt-marquee-track {
                display: flex; gap: 1rem; width: max-content;
                animation: mkt-scroll 22s linear infinite;
            }
            .mkt-marquee-outer:hover .mkt-marquee-track { animation-play-state: paused; }
            @keyframes mkt-scroll {
                from { transform: translateX(0); }
                to { transform: translateX(-50%); }
            }
            .mkt-pill {
                flex-shrink: 0; background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.12); border-radius: 999px;
                padding: 0.6rem 1.4rem; color: rgba(255,255,255,0.85);
                font-size: 0.9rem; font-weight: 600; white-space: nowrap;
            }
            /* Override the main app's light-theme card styling (white
            backgrounds, borders) that otherwise leaks into st.columns()
            containers on these dark marketing pages, causing white text
            to sit invisibly on a white background. */
            [data-testid="stHorizontalBlock"],
            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="column"],
            [data-testid="stVerticalBlock"] {
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }
        </style>
    """, unsafe_allow_html=True)


def _render_nav(active: str):
    def link(label, page, key):
        weight = "700" if active == key else "500"
        color = "#FFFFFF" if active == key else "rgba(255,255,255,0.75)"
        return f'<a href="?mkt={page}" target="_self" style="color:{color};font-weight:{weight};">{label}</a>'

    st.markdown(f"""
        <div class="mkt-nav">
            <div style="display:flex;align-items:center;gap:0.6rem;">
                <div style="width:52px;height:52px;background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                            border-radius:13px;display:flex;align-items:center;justify-content:center;
                            box-shadow:0 5px 18px rgba(45,91,255,0.45);flex-shrink:0;">
                    <span style="color:#FFFFFF;font-weight:800;font-size:1.7rem;">S</span>
                </div>
                <span class="mkt-logo">Skippr</span>
            </div>
            <div class="mkt-links">
                {link("Skippr Home", "home", "home")}
                {link("Candidate Page", "candidates", "candidates")}
                {link("Recruiter Page", "recruiters", "recruiters")}
                {link("About", "about", "about")}
            </div>
        </div>
    """, unsafe_allow_html=True)


def _render_footer():
    st.markdown("""
        <div class="mkt-footer" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:2rem;">
            <div>
                <strong style="color:#FFFFFF;font-size:1.1rem;">Skippr</strong><br>
                <span style="color:rgba(255,255,255,0.45);">From Rejection to Revolution.<br>Built to humanize hiring.</span>
            </div>
            <div>
                <div style="color:#FFFFFF;font-weight:700;margin-bottom:0.6rem;">Navigation</div>
                <a href="?mkt=home" target="_self" style="display:block;color:rgba(255,255,255,0.6);text-decoration:none;margin-bottom:0.4rem;">Skippr Home</a>
                <a href="?mkt=candidates" target="_self" style="display:block;color:rgba(255,255,255,0.6);text-decoration:none;margin-bottom:0.4rem;">Candidate Page</a>
                <a href="?mkt=recruiters" target="_self" style="display:block;color:rgba(255,255,255,0.6);text-decoration:none;margin-bottom:0.4rem;">Recruiter Page</a>
                <a href="?mkt=about" target="_self" style="display:block;color:rgba(255,255,255,0.6);text-decoration:none;">About</a>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_home():
    _inject_marketing_css()
    _render_nav("home")

    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.markdown("""
            <p class="mkt-eyebrow">
                Your career deserves more than a resume. Skippr gives you a verified
                Quality of Hire score, targeted growth coaching, and real access to
                decision-makers -- no guesswork, just results.
            </p>
            <h1 class="mkt-h1">Empowering Talent.<br>Elevating Potential.</h1>
            <a class="mkt-cta" href="?mkt=login" target="_self">Start Your Journey</a>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <img src="{HERO_IMAGE}" style="width:100%;border-radius:16px;margin-top:1rem;">
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    pills = [
        "Verified References", "Evidence-Based Matching", "Real Growth Roadmaps",
        "No Self-Reported Claims", "Backchannel Fit Checks", "Transparent Scoring",
    ]
    pills_html = "".join(f'<div class="mkt-pill">{p}</div>' for p in pills)
    st.markdown(f"""
        <div class="mkt-marquee-outer">
            <div class="mkt-marquee-track">
                {pills_html}{pills_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="mkt-section-title">Hiring Is Broken. The Numbers Prove It.</div>', unsafe_allow_html=True)

    stats = [
        ("~6 months", "is the average job search length today, according to U.S. Bureau of Labor Statistics data."),
        ("250 : 1", "is the average ratio of applications to interview invites for a single corporate job posting."),
        ("75%+", "of resumes are rejected by ATS filters before a human recruiter ever sees them."),
        ("41%", "of security and fraud leaders say their company has unknowingly hired a fraudulent candidate."),
    ]
    st1, st2, st3, st4 = st.columns(4)
    for col, (number, desc) in zip([st1, st2, st3, st4], stats):
        with col:
            st.markdown(f"""
                <div style="font-size:2.2rem;font-weight:800;
                            background:linear-gradient(135deg,#2D5BFF,#00C2A8);
                            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                            background-clip:text;margin-bottom:0.4rem;">{number}</div>
                <p class="mkt-body" style="font-size:0.88rem;">{desc}</p>
            """, unsafe_allow_html=True)
    st.markdown("""
        <p style="color:rgba(255,255,255,0.35);font-size:0.75rem;margin-top:1rem;">
            Sources: U.S. Bureau of Labor Statistics, Gartner, and industry hiring research (2025-2026).
        </p>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="mkt-section-title">Why Choose Skippr?</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
            <div class="mkt-card-title">🔍 The Next Wave of Hiring</div>
            <p class="mkt-body">Skippr's Quality of Hire (QoH) score moves beyond keywords --
            blending verified skills, behavior, education, and real references into a
            predictive, transparent signal.</p>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
            <div class="mkt-card-title">🎯 For Candidates</div>
            <p class="mkt-body">Stand out based on real strengths, not resume tricks. Build a
            verified profile, gain visibility, and follow a personalized growth roadmap to
            your next opportunity.</p>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
            <div class="mkt-card-title">💼 For Recruiters</div>
            <p class="mkt-body">Gain confidence at the top of the funnel. Skippr surfaces
            candidates with verified inputs -- reducing time to hire and improving decision
            quality.</p>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="mkt-section-title">How Skippr Works</div>', unsafe_allow_html=True)

    steps = [
        ("01", "Build Your Profile", "Upload your resume once. Skippr extracts your real skills and experience -- no manual re-entry per application."),
        ("02", "Get an Honest Match Score", "Paste a job description and get a score built from a transparent rubric, with real evidence quoted from your own resume."),
        ("03", "Add a Verified Reference", "Request a backchannel reference -- a real person answers honest fit questions, no self-reported claims a recruiter has to just trust."),
        ("04", "Follow a Real Roadmap", "Get a growth plan targeted at your specific gaps, with real course links -- not generic 30/60/90-day filler."),
    ]
    s1, s2, s3, s4 = st.columns(4)
    for col, (num, title, body) in zip([s1, s2, s3, s4], steps):
        with col:
            st.markdown(f"""
                <div style="color:#2D5BFF;font-weight:800;font-size:1.6rem;margin-bottom:0.5rem;">{num}</div>
                <div class="mkt-card-title">{title}</div>
                <p class="mkt-body" style="font-size:0.92rem;">{body}</p>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;padding:2.5rem;">
            <div class="mkt-card-title" style="font-size:1.3rem;">Why I Built Skippr</div>
            <p class="mkt-body" style="font-size:1.05rem;font-style:italic;">
                "I didn't get the job. I built the platform that fixes the problem. AI made it
                easy to fake a great resume -- Skippr is the verification layer hiring was
                missing: real references, real evidence, real people, on both sides of the hire."
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align:center;background:linear-gradient(135deg, rgba(45,91,255,0.12), rgba(0,194,168,0.08));
                    border-radius:20px;padding:3rem 2rem;">
            <div class="mkt-section-title" style="margin-bottom:1rem;">Your Career, Finally Verified.</div>
            <p class="mkt-body" style="max-width:500px;margin:0 auto 1.5rem auto;">
                Build a profile that proves what your resume can't. Free to start.
            </p>
            <a class="mkt-cta" href="?mkt=login" target="_self">Get Started</a>
        </div>
    """, unsafe_allow_html=True)

    _render_footer()


def render_candidates():
    _inject_marketing_css()
    _render_nav("candidates")

    col1, col2 = st.columns([1, 1.1])
    with col1:
        st.markdown('<div class="mkt-section-title">Your Growth, Quantified.</div>', unsafe_allow_html=True)
        st.markdown("""
            <div class="mkt-card-title">Know Where You Stand</div>
            <p class="mkt-body">Skippr turns your resume, skills, and references into a
            transparent Quality of Hire score, showing exactly how you match the roles you want.</p>
            <br>
            <div class="mkt-card-title">See the Path Forward</div>
            <p class="mkt-body">Your profile includes a 30/60/90-day growth roadmap built around
            your specific gaps -- helping you improve and stand out before you even apply.</p>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<img src="{CANDIDATE_IMAGE}" style="width:100%;border-radius:16px;">""", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="mkt-section-title">Reduce the No-Reply Rejection E-mails</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
            <div class="mkt-card-title">Stand Out with Verified Skills</div>
            <p class="mkt-body">Real people vouch for your work through Skippr's backchannel
            references -- not a self-reported list a recruiter has to take on faith.</p>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
            <div class="mkt-card-title">Control Your Growth Path</div>
            <p class="mkt-body">Build your roadmap around real gaps identified against the
            specific roles you're targeting, with real course links to close them.</p>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
            <div class="mkt-card-title">Visibility Where It Matters</div>
            <p class="mkt-body">Verified profiles surface directly to recruiters actively
            hiring, so your credibility does the work of getting you noticed.</p>
        """, unsafe_allow_html=True)

    st.markdown('<a class="mkt-cta" href="?mkt=login" target="_self">Build Your Profile</a>', unsafe_allow_html=True)
    _render_footer()


def render_recruiters():
    _inject_marketing_css()
    _render_nav("recruiters")

    col1, col2 = st.columns([1, 1.1])
    with col1:
        st.markdown('<div class="mkt-section-title">Hire With Confidence, Not Guesswork.</div>', unsafe_allow_html=True)
        st.markdown("""
            <div class="mkt-card-title">See Beyond the Resume</div>
            <p class="mkt-body">Every candidate's Quality of Hire score is built from verified
            references and evidence-backed skill matches -- not just keywords an AI can fake.</p>
            <br>
            <div class="mkt-card-title">Verified From Day One</div>
            <p class="mkt-body">Skippr addresses the fastest-growing risk in hiring: fake
            candidates and unverifiable claims. Every profile you see has a real human backchannel
            behind it.</p>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<img src="{RECRUITER_IMAGE}" style="width:100%;border-radius:16px;">""", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="mkt-section-title">Stop Losing Time to Bad-Fit Hires</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
            <div class="mkt-card-title">Real-Time Quality Signals</div>
            <p class="mkt-body">Compare candidates on one consistent, explainable score --
            weighted skills, experience, and domain fit, not a black box.</p>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
            <div class="mkt-card-title">Backchannel Insights</div>
            <p class="mkt-body">Read real answers from people who've actually worked with each
            candidate -- fit, work style, and honest recommendations.</p>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
            <div class="mkt-card-title">Faster, Fairer Decisions</div>
            <p class="mkt-body">Every hire/pass decision you make helps calibrate the platform
            toward what "great" actually looks like on your team.</p>
        """, unsafe_allow_html=True)

    st.markdown('<a class="mkt-cta" href="?mkt=login" target="_self">See Your Candidates</a>', unsafe_allow_html=True)
    _render_footer()


def render_about():
    _inject_marketing_css()
    _render_nav("about")

    st.markdown('<div class="mkt-section-title">Rethinking Hiring Through Quality</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class="mkt-card-title">Why Skippr Exists</div>
            <p class="mkt-body">We're changing how talent gets evaluated. Quality of Hire (QoH)
            blends resume evidence, behavior, verified references, and education into one clear
            score -- making hiring smarter, faster, and more fair.</p>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class="mkt-card-title">What It Means for You</div>
            <p class="mkt-body">Candidates gain visibility, coaching, and control. Recruiters get
            high-signal profiles, fewer surprises, and more confident decisions. AI sorts the
            noise -- humans make the match.</p>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div class="mkt-card-title">From Rejection to Revolution</div>
        <p class="mkt-body">Skippr started with a simple, personal problem: a great candidate
        gets rejected without explanation, while an unqualified one slips through on a
        well-formatted resume. We built the platform that fixes that -- real verification,
        real evidence, real people, on both sides of the hire.</p>
    """, unsafe_allow_html=True)

    st.markdown('<a class="mkt-cta" href="?mkt=login" target="_self">Start Your Journey</a>', unsafe_allow_html=True)
    _render_footer()


def render_marketing_page(page: str):
    """Dispatches to the correct marketing page based on the `mkt` query param."""
    if page == "candidates":
        render_candidates()
    elif page == "recruiters":
        render_recruiters()
    elif page == "about":
        render_about()
    else:
        render_home()
