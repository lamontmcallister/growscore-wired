# Full Skippr platform with all modules and updated login UI


import streamlit as st
import os
import openai
import ast
import pdfplumber
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="Skippr", layout="wide")

st.markdown("""
# 🌟 Welcome to Skippr
**Human-first hiring. Verified skills. Smarter decisions.**

At Skippr, we believe great talent shouldn’t get lost in outdated filters or keyword games.  
We use AI to surface the *real signals* behind your resume—so you can show what you're capable of, not just what you've done.

**Why Skippr?**
- ✅ Verifies your resume data with AI  
- 🔍 Matches you to job descriptions semantically, not just by title  
- 📈 Builds a personalized growth roadmap  
- 🤝 Helps recruiters see *you*, not just your job history

Let’s skip the noise—and unlock your potential.
""")

st.markdown("""
# 🌟 Welcome to Skippr
**Human-first hiring. Verified skills. Smarter decisions.**

At Skippr, we believe great talent shouldn’t get lost in outdated filters or keyword games.  
We use AI to surface the *real signals* behind your resume—so you can show what you're capable of, not just what you've done.

**Why Skippr?**
- ✅ Verifies your resume data with AI  
- 🔍 Matches you to job descriptions semantically, not just by title  
- 📈 Builds a personalized growth roadmap  
- 🤝 Helps recruiters see *you*, not just your job history

Let’s skip the noise—and unlock your potential.
""")

portal = st.radio("Choose your portal:", ["👤 Candidate Portal", "🧑‍💼 Recruiter Portal"])
if portal == "👤 Candidate Portal":
    candidate_journey()
else:
    recruiter_dashboard()
