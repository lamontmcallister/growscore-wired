import streamlit as st
from openai import OpenAI

@st.cache_resource
def get_openai_client() -> OpenAI:
    """Returns a cached OpenAI client, created once and reused."""
    return OpenAI(api_key=st.secrets["openai"]["key"])
