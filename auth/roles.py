def get_user_role(user) -> str:
    """
    Server-side role check. Reads role from Supabase auth user_metadata rather
    than trusting a client-side toggle. Defaults to 'candidate' if unset.

    To grant recruiter access, set user_metadata.role = "recruiter" for that
    user in Supabase (Dashboard > Authentication > Users > Edit, or via the
    admin API). Do NOT gate recruiter access on anything the client controls.
    """
    if not user:
        return "candidate"
    metadata = getattr(user, "user_metadata", None) or {}
    role = metadata.get("role", "candidate")
    return role if role in ("candidate", "recruiter") else "candidate"
