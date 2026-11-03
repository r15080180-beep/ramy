# 🧭 AI Learning Roadmap Generator

A beginner-friendly web app that builds a **personalised learning roadmap** for any field or skill. You choose a topic, your level and how much time you have. Google Gemini AI then writes a full plan with stages, projects, free resources and a weekly schedule.

Built with Python, Streamlit and the Google Gemini API. It is ready to upload to GitHub and deploy on Streamlit Community Cloud.

---

## ✨ Features

- Enter any **field or domain** (Data Science, Cybersecurity, Python, Web Development ...).
- Choose your **skill level** (Beginner, Intermediate, Advanced).
- Choose your **available time** (1 Month, 3 Months, 6 Months, 1 Year).
- Choose your **daily study hours** (1 to 4 hours).
- Add an optional **learning goal**.
- A **study plan overview** (table and chart) that splits your time into four stages. It is calculated with NumPy and pandas.
- An AI-written roadmap with these sections:
  introduction, prerequisites, learning stages (topics, tools and a project for every stage), Python libraries and tools, free resources, YouTube channels and documentation, weekly schedule, practice exercises, final portfolio project, career opportunities and next steps.
- Clear sections in **expandable panels**.
- **Download** the roadmap as Markdown (`.md`) or text (`.txt`).
- **Reset** button, loading spinner and simple English error messages.
- Handles empty inputs, invalid API keys, quota limits, internet problems and empty AI answers.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.10+ | Main programming language |
| Streamlit | Web interface |
| Google Gemini API (`google-genai` SDK) | AI roadmap generation |
| pandas | Study-plan table |
| NumPy | Splitting your time into stages |
| GitHub | Storing the project |
| Claude AI | Generating and reviewing the code |

---

## 📁 Project Structure

```
ai-learning-roadmap-generator/
├── app.py                  # The whole application
├── requirements.txt        # Python libraries
├── README.md               # This file
├── .gitignore              # (you create this) keeps your API key out of GitHub
└── .streamlit/
    └── secrets.toml        # (you create this, local only) holds your API key
```

The first three files are the project. `.gitignore` and `.streamlit/secrets.toml` are small files you create yourself in the steps below.

---

## 💻 Installation

1. **Install Python 3.10 or newer** from https://www.python.org/downloads/ (tick "Add Python to PATH" on Windows).
2. **Put the three project files in one folder**, then open a terminal in that folder.
3. **Create a virtual environment** (recommended):

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install the libraries:**

   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 How to Get a Gemini API Key

1. Go to **Google AI Studio**: https://aistudio.google.com/
2. Sign in with your Google account.
3. Click **Get API key**, then **Create API key**.
4. Copy the key and keep it private. Never post it online or put it in your code.

Google offers a free tier for some models. Free-tier limits and model availability can change, so check the current limits in AI Studio.

---

## 🔐 How to Configure the API Key (Secrets)

The app reads the key from **Streamlit secrets** under the name `GEMINI_API_KEY`. The key is never written in the code.

### Locally

1. Create a folder named `.streamlit` inside the project folder.
2. Inside it, create a file named `secrets.toml` with this content:

   ```toml
   GEMINI_API_KEY = "paste-your-key-here"
   ```

3. Create a file named `.gitignore` in the project folder so the key is **never uploaded to GitHub**:

   ```
   .streamlit/secrets.toml
   venv/
   __pycache__/
   ```

### On Streamlit Community Cloud

1. Open your app on https://share.streamlit.io/
2. Click **⋮ (three dots)** next to the app, then **Settings**, then **Secrets**.
3. Paste this and click **Save**:

   ```toml
   GEMINI_API_KEY = "paste-your-key-here"
   ```

4. The app restarts and picks up the key.

---

## ▶️ Run the App Locally

```bash
streamlit run app.py
```

Your browser opens at http://localhost:8501. In the sidebar, the **Status** box should say "Gemini API key found".

---

## 🔄 How to Change the Gemini Model

Google retires old models from time to time, so the model name is easy to change. The app uses `gemini-3.1-flash-lite` by default.

**Option 1: no code change (recommended).** Add one line to your secrets (local file or Streamlit Cloud):

```toml
GEMINI_MODEL = "gemini-3.8-flash"
```

**Option 2: edit the code.** In `app.py`, change this line near the top:

```python
DEFAULT_MODEL = "gemini-3.1-flash-lite"
```

Find the current model names at https://ai.google.dev/gemini-api/docs/models and the retirement dates at https://ai.google.dev/gemini-api/docs/deprecations. Names ending in `-preview` can change or disappear sooner than stable names. Older `gemini-2.0-*` models are already shut down, and `gemini-2.5-*` models were scheduled to shut down in October 2026, so avoid them.

---

## 🐙 Upload the Project to GitHub

1. Create a free account at https://github.com/
2. Click **New repository**. Name it, for example, `ai-learning-roadmap-generator`. Choose **Public** (Streamlit Community Cloud's free plan works best with public repos) and click **Create repository**.
3. Make sure `.gitignore` exists (see above) so `secrets.toml` is not uploaded.
4. In your project folder, run:

   ```bash
   git init
   git add app.py requirements.txt README.md .gitignore
   git commit -m "Add AI Learning Roadmap Generator"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/ai-learning-roadmap-generator.git
   git push -u origin main
   ```

5. Refresh the GitHub page. You should see your files. Check that `secrets.toml` is **not** there.

---

## ☁️ Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io/ and sign in with GitHub.
2. Click **Create app** (or **New app**) and choose **Deploy a public app from GitHub**.
3. Select your repository, the branch `main`, and the main file path `app.py`.
4. Open **Advanced settings**, paste your secret into the **Secrets** box:

   ```toml
   GEMINI_API_KEY = "paste-your-key-here"
   ```

5. Click **Deploy**. After a minute or two you get a public link to share.

---

## 🧯 Common Errors and Solutions

| Message or problem | What it means | Fix |
|---|---|---|
| "The Gemini API key is missing" | The app cannot find `GEMINI_API_KEY`. | Create `.streamlit/secrets.toml` locally, or add the key under **Settings → Secrets** on Streamlit Cloud. Restart the app. |
| "Your Gemini API key was not accepted" | The key is wrong, has extra spaces or quotes, was deleted, or Gemini is not available in your region. | Create a new key in Google AI Studio and paste it again. |
| "You have reached the Gemini usage limit (quota)" | You made too many requests for the free tier. | Wait a minute and try again, or wait until tomorrow. You can also try another model name. |
| "The Gemini model '...' was not found" | The model name is wrong or the model was retired. | Change the model name (see "How to Change the Gemini Model"). |
| "Could not connect to Google's servers" | No internet, or a firewall or VPN is blocking Google. | Check your connection, turn off the VPN or proxy, and try again. |
| "Gemini did not return any text" | The answer was empty or blocked by safety filters. | Click Generate again or change the field or goal slightly. |
| "Please enter a field or domain" | The field box was empty. | Type a topic such as `Data Science`. |
| `ModuleNotFoundError: No module named 'streamlit'` (or `google`) | The libraries are not installed in the active environment. | Activate your virtual environment and run `pip install -r requirements.txt`. |
| `streamlit: command not found` | Streamlit is not installed or the environment is not active. | Run `python -m streamlit run app.py`. |
| App on Streamlit Cloud shows an error after deploy | A secret is missing or `requirements.txt` was not found. | Check **Settings → Secrets** and that `requirements.txt` is in the repository's main folder. |
| The roadmap is not split into sections | Gemini ignored the heading format. | Click Generate again. The full text is still shown and downloadable. |

---

## ⚠️ Good to Know

- Roadmaps are written by AI and can contain mistakes. Check courses, tools and career advice before relying on them. The app asks Gemini to name resources instead of giving links, because AI can invent web addresses.
- Each click on **Generate Roadmap** uses your Gemini quota.
- Never share your API key or commit `secrets.toml` to GitHub. If you leak a key by accident, delete it in Google AI Studio and create a new one.

---

## 📄 License

Free to use for learning and personal projects.# ramy
