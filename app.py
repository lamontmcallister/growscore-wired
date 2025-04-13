
import streamlit as st
import pdfplumber

st.set_page_config(page_title="GrowScore", layout="wide")

def extract_text_from_pdf(uploaded_file):
    if uploaded_file is not None:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "".join([page.extract_text() for page in pdf.pages])
        return text
    return ""

st.title("GrowScore – Candidate Journey")

st.session_state.demo_mode = st.sidebar.checkbox("Demo Mode", value=False)

uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

if uploaded_file:
    resume_text = extract_text_from_pdf(uploaded_file)
    st.session_state.resume_text = resume_text
    st.text_area("Extracted Resume Text", resume_text, height=300)

# Placeholder for job descriptions and JD match
st.subheader("📄 Step 8: Resume vs JD Skill Match")
jd1 = st.text_area("Paste JD 1", key="jd_1")
jd2 = st.text_area("Paste JD 2", key="jd_2")
jd_inputs = [jd for jd in [jd1, jd2] if jd.strip()]
if jd_inputs and "resume_text" in st.session_state:
    st.write("Matching resume to job descriptions (placeholder logic)...")
    for i, jd in enumerate(jd_inputs):
        st.write(f"**JD {i+1}** Match Score: {round(75 + i*5, 1)}%")  # Dummy match score

# Placeholder for final summary
st.subheader("✅ Step 9: Final Summary & Growth Roadmap")
jd_scores = [80, 85]  # Dummy scores
avg_jd = round(sum(jd_scores) / len(jd_scores), 1)
skill_score = 70
ref_score = 90
behavior = 50
qoh = round((skill_score + ref_score + behavior + avg_jd) / 4, 1)
st.metric("💡 Quality of Hire Score", f"{qoh}/100")

st.subheader("🔍 Verification Table")
st.table({
    "Resume": ["✅ GPT Verified"],
    "References": ["✅ Sent"],
    "Backchannel": ["❌"],
    "Education": ["❌"],
    "HR Performance": ["❌"],
    "Behavior": ["🟠 Self-Reported"],
    "JD Match": [f"{avg_jd}%"]
})

st.subheader("📈 Growth Roadmap")
st.markdown("- Take an advanced Excel course")
st.markdown("- Improve leadership skills via Coursera")
st.markdown("- Add GitHub portfolio")
st.success("🎉 You’ve completed your GrowScore profile!")
