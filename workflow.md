# AI Study Pack Generator — Workflow

## Purpose
Generate a personalized study pack from a learner's subject, skill level, available
time, weekly study hours, goal, and learning preference.

## Workflow stages

1. **Input validation**
   - Require a subject and duration.
   - Validate numeric study hours through the Streamlit widget.
   - Read the Groq API key from environment variables or Streamlit secrets.
2. **Planning**
   - Inputs: learner profile.
   - Output: objectives, prerequisites, weekly plan, milestones, final project.
3. **Content generation**
   - Inputs: learner profile + plan.
   - Output: explanations, notes, examples, glossary, optional resources.
4. **Assessment generation**
   - Inputs: learner profile + plan + content.
   - Output: quiz questions, answer explanations, and hands-on exercises.
5. **Review**
   - Inputs: learner profile + plan + content + assessment.
   - Output: approval decision, score, strengths, and issues.
6. **Conditional refinement**
   - If the reviewer approves and reports no issues, keep the pack.
   - Otherwise, pass all prior artifacts and review feedback to the refinement stage.
7. **Display/export**
   - Show the pack in Streamlit tabs.
   - Allow download as JSON or Markdown.

## Context passing
Each stage receives structured JSON from previous stages. The plan is passed to both
content and assessment generation, while the review stage receives all generated
artifacts. Refinement receives the full context plus reviewer feedback.

## Error handling
- Missing subject, duration, or API key: show a user-facing message and stop.
- Groq/API/model error: catch the exception, show a concise error, and expose technical
  details in an expandable panel.
- Invalid JSON: attempt to extract a JSON object from surrounding code fences/text;
  if parsing still fails, stop the workflow with a clear stage-specific error.
- No automatic retry loop is used in this starter version, to avoid repeated API calls
  and unexpected usage costs. The user can retry manually.

## Notes
- LLM review is a quality check, not a guarantee of factual correctness.
- Verify important educational content and external resources before relying on them.
- For production, consider schema validation, bounded retries, logging, caching, and
  stronger resource verification.
