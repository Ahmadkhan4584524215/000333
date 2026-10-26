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
