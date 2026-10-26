import json
import os
import re
from typing import Any, Dict

import streamlit as st
from groq import Groq

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
    """Read the API key from Streamlit secrets or an environment variable."""
    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""
    return secret_key or os.getenv("GROQ_API_KEY", "")


def extract_json(text: str) -> Any:
    """Parse JSON from an LLM response, tolerating surrounding code fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise ValueError("The model did not return valid JSON.")


def call_groq(client: Groq, model: str, system_prompt: str, user_payload: Dict[str, Any]) -> str:
    """Call Groq and return the assistant text."""
    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
            },
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The model returned an empty response.")
    return content


def run_stage(
    client: Groq,
    model: str,
    stage_name: str,
    system_prompt: str,
    payload: Dict[str, Any],
) -> Any:
    """Run one workflow stage, parse its JSON output, and show progress."""
    with st.status(f"{stage_name}...", expanded=True) as status:
        try:
            raw = call_groq(client, model, system_prompt, payload)
            parsed = extract_json(raw)
            status.update(label=f"{stage_name} complete", state="complete")
            return parsed
        except Exception as exc:
            status.update(label=f"{stage_name} failed", state="error")
            raise RuntimeError(f"{stage_name} failed: {exc}") from exc


def generate_study_pack(
    client: Groq,
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
            "Groq API key not found. Set GROQ_API_KEY in your environment "
            "or add it to Streamlit secrets."
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
   
   model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    try:
        client = Groq(api_key=api_key)
        with st.spinner("Building your personalized study pack..."):
            pack = generate_study_pack(client, model, learner)

        st.session_state["study_pack"] = pack
        st.session_state["study_pack_field"] = field.strip()
        st.success("Your study pack is ready.")
    except Exception as exc:
        st.error(
            "The workflow could not finish. Check your API key, model name, "
            "internet connection, and Groq usage limits, then try again."
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
