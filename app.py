import json
import os
import re
from typing import Any, Dict

import streamlit as st
from google import genai
from google.genai import types

from prompts import (
    PLANNER_PROMPT,
    CONTENT_PROMPT,
    ASSESSMENT_PROMPT,
    REVIEW_PROMPT,
    REFINEMENT_PROMPT,
)

st.set_page_config(
    page_title="AI Study Pack Generator",
    page_icon="📚",
    layout="wide",
)

st.title("📚 AI Study Pack Generator")
st.write(
    "Create a personalized study pack through a multi-stage AI workflow: "
    "planning, content generation, assessment, review, and refinement."
)


def get_api_key() -> str:
    """Read a Google AI Studio Gemini API key from Streamlit secrets or env."""
    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        try:
            secret_key = st.secrets.get(key_name, "")
        except Exception:
            secret_key = ""
        if secret_key:
            return secret_key
        env_key = os.getenv(key_name, "")
        if env_key:
            return env_key
    return ""


def extract_json(text: str) -> Any:
    """Parse JSON from an LLM response, tolerating surrounding code fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as first_error:
        # Some responses include a short preamble despite the JSON-only prompt.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            candidate = cleaned[start : end + 1]
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                context_start = max(0, exc.pos - 180)
                context_end = min(len(candidate), exc.pos + 180)
                excerpt = candidate[context_start:context_end]
                raise ValueError(
                    f"The model returned malformed JSON at line {exc.lineno}, "
                    f"column {exc.colno}: {exc.msg}. Near the error: {excerpt}"
                ) from exc
        else:
            context_start = max(0, first_error.pos - 180)
            context_end = min(len(cleaned), first_error.pos + 180)
            excerpt = cleaned[context_start:context_end]
            raise ValueError(
                f"The model did not return valid JSON. Near the error: {excerpt}"
            ) from first_error

    if not isinstance(parsed, (dict, list)):
        raise ValueError("The model returned JSON, but it was not an object or array.")
    return parsed


def call_gemini(client: genai.Client, model: str, system_prompt: str, user_payload: Dict[str, Any]) -> str:
    """Call Gemini and request structured JSON output."""
    response = client.models.generate_content(
        model=model,
        contents=json.dumps(user_payload, ensure_ascii=False, indent=2),
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    content = response.text
    if not content:
        raise ValueError("Gemini returned an empty response. Try again or check the model/API key.")
    return content


def run_stage(
    client: genai.Client,
    model: str,
    stage_name: str,
    system_prompt: str,
    payload: Dict[str, Any],
) -> Any:
    """Run one workflow stage, parse its JSON output, and show progress."""
    with st.status(f"{stage_name}...", expanded=True) as status:
        try:
            raw = call_gemini(client, model, system_prompt, payload)
            parsed = extract_json(raw)
            status.update(label=f"{stage_name} complete", state="complete")
            return parsed
        except Exception as exc:
            status.update(label=f"{stage_name} failed", state="error")
            raise RuntimeError(f"{stage_name} failed: {exc}") from exc


def generate_study_pack(
    client: genai.Client,
    model: str,
    learner: Dict[str, Any],
) -> Dict[str, Any]:
    """Run planning -> content -> assessment -> review -> optional refinement."""
    plan = run_stage(
        client, model, "Stage 1/5: Planning", PLANNER_PROMPT,
        {"learner": learner},
    )

    content = run_stage(
        client, model, "Stage 2/5: Content generation", CONTENT_PROMPT,
        {"learner": learner, "plan": plan},
    )

    assessment = run_stage(
        client, model, "Stage 3/5: Assessment generation", ASSESSMENT_PROMPT,
        {"learner": learner, "plan": plan, "content": content},
    )

    review = run_stage(
        client, model, "Stage 4/5: Review", REVIEW_PROMPT,
        {
            "learner": learner,
            "plan": plan,
            "content": content,
            "assessment": assessment,
        },
    )

    issues = review.get("issues", [])
    if review.get("approved", False) and not issues:
        final_pack = {
            "learner_profile": learner,
            "plan": plan,
            "content": content,
            "assessment": assessment,
            "review": review,
            "refinement": {"performed": False, "reason": "Review approved the pack."},
        }
    else:
        final_pack = run_stage(
            client, model, "Stage 5/5: Refinement", REFINEMENT_PROMPT,
            {
                "learner": learner,
                "plan": plan,
                "content": content,
                "assessment": assessment,
                "review": review,
            },
        )
        # Keep the intermediate outputs visible in the exported artifact too.
        final_pack.setdefault("learner_profile", learner)
        final_pack.setdefault("review", review)
        final_pack.setdefault("refinement", {"performed": True})

    return final_pack


with st.sidebar:
    st.header("Learner details")
    field = st.text_input("What do you want to study?", placeholder="e.g., Python programming")
    level = st.selectbox("Current skill level", ["Beginner", "Intermediate", "Advanced"])
    duration = st.text_input("Time available", value="4 weeks", placeholder="e.g., 6 weeks")
    hours_per_week = st.number_input("Study hours per week", min_value=1, max_value=60, value=5)
    goal = st.text_area("Learning goal", placeholder="e.g., Build a small web application")
    learning_style = st.selectbox(
        "Preferred learning style",
        ["Balanced", "Project-based", "Reading and notes", "Practice and quizzes"],
    )
    include_resources = st.checkbox("Include resource suggestions", value=True)
    generate = st.button("Generate study pack", type="primary", use_container_width=True)

st.caption("Tip: Be specific about your topic and goal for a more useful study pack.")

if generate:
    if not field.strip():
        st.error("Please enter a subject or field to study.")
        st.stop()
    if not duration.strip():
        st.error("Please enter how much time you have.")
        st.stop()

    api_key = get_api_key()
    if not api_key:
        st.error(
            "Google AI Studio API key not found. Set GEMINI_API_KEY in your environment "
            "or add it to Streamlit secrets (GOOGLE_API_KEY also works)."
        )
        st.stop()

    learner = {
        "field": field.strip(),
        "skill_level": level,
        "available_time": duration.strip(),
        "study_hours_per_week": int(hours_per_week),
        "goal": goal.strip() or "Build a solid understanding of the subject",
        "learning_style": learning_style,
        "include_resource_suggestions": include_resources,
    }
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    try:
        client = genai.Client(api_key=api_key)
        with st.spinner("Building your personalized study pack..."):
            pack = generate_study_pack(client, model, learner)

        st.session_state["study_pack"] = pack
        st.session_state["study_pack_field"] = field.strip()
        st.success("Your study pack is ready.")
    except Exception as exc:
        st.error(
            "The workflow could not finish. Check your Google AI Studio API key, "
            "Gemini model name, internet connection, and API quota, then try again."
        )
        with st.expander("Technical details"):
            st.code(str(exc))

if "study_pack" in st.session_state:
    pack = st.session_state["study_pack"]
    st.subheader(f"Study pack: {st.session_state.get('study_pack_field', 'Your subject')}")

    tabs = st.tabs(["Overview", "Learning plan", "Study content", "Assessment", "Review", "Raw JSON"])
    with tabs[0]:
        st.markdown("### Learner profile")
        st.json(pack.get("learner_profile", {}))
        if pack.get("plan"):
            st.markdown("### Plan summary")
            st.json(pack["plan"])
    with tabs[1]:
        plan = pack.get("plan", {})
        st.json(plan)
    with tabs[2]:
        st.json(pack.get("content", {}))
    with tabs[3]:
        st.json(pack.get("assessment", {}))
    with tabs[4]:
        st.json(pack.get("review", {}))
        if pack.get("refinement"):
            st.markdown("### Refinement")
            st.json(pack["refinement"])

    json_text = json.dumps(pack, ensure_ascii=False, indent=2)
    st.download_button(
        "⬇️ Download study pack (JSON)",
        data=json_text,
        file_name="study_pack.json",
        mime="application/json",
    )
    st.download_button(
        "⬇️ Download study pack (Markdown)",
        data="# AI Study Pack\n\n```json\n" + json_text + "\n```\n",
        file_name="study_pack.md",
        mime="text/markdown",
    )
