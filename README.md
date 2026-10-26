# AI Study Pack Generator

A beginner-friendly Streamlit app that uses the Groq API to generate a personalized
study pack through a multi-stage workflow.

## Files
- `app.py` — Streamlit UI and workflow orchestration
- `prompts.py` — stage-specific system prompts
- `workflow.md` — workflow, context passing, and error handling
- `requirements.txt` — Python dependencies

## Run locally
1. Install Python 3.10+.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Groq key as an environment variable:
   - macOS/Linux: `export GROQ_API_KEY="your-key"`
   - Windows PowerShell: `$env:GROQ_API_KEY="your-key"`
4. Start the app:
   ```bash
   streamlit run app.py
   ```

Optional model override:
- Set `GROQ_MODEL` to a model currently available to your Groq account.
- The default in this starter app is `llama-3.3-70b-versatile`; change it if Groq
  deprecates it or your account does not have access.

## Deploy on Streamlit Community Cloud
1. Upload these files to a GitHub repository.
2. Create a new app in Streamlit Community Cloud and select `app.py`.
3. In the app's Secrets settings, add:
   ```toml
   GROQ_API_KEY = "your-key"
   ```
4. Deploy. Never commit the real API key to GitHub.

## Google Colab development
Colab can be used to write and test the files, but it is a temporary notebook
environment. For a stable public deployment, push the project files to GitHub and
deploy them with Streamlit Community Cloud.
