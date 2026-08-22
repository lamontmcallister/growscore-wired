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


def get_fresh_anon_client() -> Client:
    """
    Creates a brand-new, uncached Supabase client instance -- deliberately
    NOT using @st.cache_resource. The cached get_supabase_client() is shared
    across every user session on the server; if any user is logged in, that
    shared client can carry their auth token into unrelated requests. The
    public reference-response page has no logged-in user by design, so it
    must use a guaranteed-clean client to actually hit RLS as 'anon', not
    whatever role happens to be cached from someone else's session.
    """
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)
