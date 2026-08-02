import json
from ai.client import get_openai_client


def call_openai_json(prompt: str, temperature: float = 0.3):
    """
    Calls OpenAI's chat completions endpoint (openai>=1.0 client) and asks for
    strict JSON back so we don't depend on ast.literal_eval parsing whatever
    prose the model feels like returning.

    Returns (data, error). On failure, `data` is None and `error` holds a
    human-readable message -- callers must surface this to the user rather
    than silently substituting fabricated values.
    """
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You respond only with valid JSON. No prose, no markdown fences."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"AI returned unparseable output: {e}"
    except Exception as e:
        return None, f"AI request failed: {e}"


def extract_skills_from_resume(text):
    prompt = (
        "Extract 5-10 professional skills from this resume. "
        'Respond as JSON: {"skills": ["skill1", "skill2", ...]}\n\n'
        f"Resume:\n{text}"
    )
    data, error = call_openai_json(prompt)
    if error:
        return [], error
    return data.get("skills", []), None


def extract_contact_info(text):
    prompt = (
        "From this resume, extract the full name, email, and job title. "
        'Respond as JSON: {"name": "...", "email": "...", "title": "..."}\n\n'
        f"Resume:\n{text}"
    )
    data, error = call_openai_json(prompt)
    if error:
        return {"name": "", "email": "", "title": ""}, error
    return data, None


def match_resume_to_jds(resume_text, jd_texts):
    prompt = f"Given this resume:\n{resume_text}\n\nMatch semantically to the following job descriptions:\n"
    for i, jd in enumerate(jd_texts):
        prompt += f"\nJD {i+1}:\n{jd}\n"
    prompt += '\nRespond as JSON: {"scores": [82, 76]} -- one 0-100 match score per JD, in order.'
    data, error = call_openai_json(prompt)
    if error:
        return [], error
    return data.get("scores", []), None


def match_resume_to_jd(resume_text, jd_text):
    """
    Compares a resume to a single job description and returns a detailed,
    explainable, evidence-grounded match: an overall score, matched skills
    each tied to a specific line or achievement from the resume (not just a
    skill name), and missing skills each with a short note on why that gap
    matters for this specific role. This is what powers both the Step 8 JD
    Match display and the Step 10 roadmap.

    Uses an explicit weighted rubric (skills coverage 50%, experience level
    30%, domain relevance 20%) rather than letting the model freely guess a
    number -- this makes the score more consistent and defensible, since the
    same resume against the same JD should score the same way each time.
    """
    prompt = (
        "Compare this resume to the job description below using this exact rubric "
        "-- score each dimension, then compute the overall score as the weighted sum:\n\n"
        "1. Required skills/qualifications coverage (50% weight): what fraction of the "
        "JD's explicitly stated requirements does the resume demonstrate evidence for?\n"
        "2. Relevant experience level (30% weight): does the resume's years/seniority/scope "
        "of experience match what the JD is asking for?\n"
        "3. Domain/industry relevance (20% weight): how closely does the resume's industry "
        "and functional background align with this specific role?\n\n"
        "Compute score = round(skills_coverage*0.5 + experience_level*0.3 + domain_relevance*0.2), "
        "each sub-score on a 0-100 scale before weighting.\n\n"
        "For skills/qualifications the resume DOES demonstrate, list them as "
        "matched_skills -- for each one, include a short 'evidence' quote or "
        "close paraphrase of the specific line/achievement in the resume that "
        "supports it (under 20 words, drawn directly from the resume text).\n\n"
        "For skills/qualifications the resume does NOT clearly demonstrate, list "
        "them as missing_skills -- for each one, include a short 'why_it_matters' "
        "note (under 20 words) explaining why this role specifically needs it.\n\n"
        "Keep each skill name short (2-4 words). Be consistent: the same resume "
        "against the same JD should always score the same way.\n\n"
        'Respond as JSON: {"score": 0-100, '
        '"matched_skills": [{"skill": "...", "evidence": "..."}], '
        '"missing_skills": [{"skill": "...", "why_it_matters": "..."}]}\n\n'
        f"Resume:\n{resume_text}\n\nJob Description:\n{jd_text}"
    )
    # Low temperature -- we want this score to be as reproducible as possible
    # across runs, since it's used for real comparisons between candidates.
    data, error = call_openai_json(prompt, temperature=0.1)
    if error:
        return None, error
    return data, None
