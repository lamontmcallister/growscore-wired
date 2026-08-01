import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client. @st.cache_resource means Streamlit
    creates this once and reuses it across reruns, instead of reconnecting
    on every interaction.
    """
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)
