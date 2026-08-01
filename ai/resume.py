import json
from ai.client import get_openai_client


def call_openai_json(prompt: str, temperature: float = 0.3):
    """
    Calls OpenAI's chat completions endpoint (openai>=1.0 client) and asks for
    strict JSON back so we don't depend on ast.literal_eval parsing whatever
    prose the model feels like returning.

    Returns (data, error). On failure, `data` is None and `error` holds a
    human-readable message — callers must surface this to the user rather
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
    prompt += '\nRespond as JSON: {"scores": [82, 76]} — one 0-100 match score per JD, in order.'
    data, error = call_openai_json(prompt)
    if error:
        return [], error
    return data.get("scores", []), None
