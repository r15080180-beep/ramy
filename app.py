"""
AI Learning Roadmap Generator
=============================
A Streamlit app that uses the Google Gemini API (via the official
`google-genai` SDK) to build a personalised learning roadmap.

Run locally:   streamlit run app.py
API key:       set GEMINI_API_KEY in .streamlit/secrets.toml (local)
               or in the "Secrets" box on Streamlit Community Cloud.
"""

import os
import re
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
from google import genai
from google.genai import errors, types

# ---------------------------------------------------------------------------
# 1. SETTINGS  (the easy things to change are all here)
# ---------------------------------------------------------------------------

# Gemini model used to write the roadmap.
# To change it, either edit the line below OR add  GEMINI_MODEL = "model-name"
# to your Streamlit secrets (no code change needed).
# Check https://ai.google.dev/gemini-api/docs/models for current model names.
DEFAULT_MODEL = "gemini-3.1-flash-lite"

REQUEST_TIMEOUT_MS = 120_000  # wait up to 2 minutes for Gemini to answer
STUDY_DAYS_PER_WEEK = 6  # we assume one rest day per week

LEVELS = ["Beginner", "Intermediate", "Advanced"]

# Label shown to the user -> number of weeks
DURATIONS = {"1 Month": 4, "3 Months": 13, "6 Months": 26, "1 Year": 52}

# Label shown to the user -> hours per day
DAILY_HOURS = {"1 Hour": 1, "2 Hours": 2, "3 Hours": 3, "4 Hours": 4}

# The four stages every roadmap is split into
STAGE_NAMES = [
    "Stage 1: Foundations",
    "Stage 2: Core Skills",
    "Stage 3: Applied Practice",
    "Stage 4: Portfolio & Career Prep",
]

# Share of total time spent in each stage, depending on the learner's level.
# (Each row adds up to 1.0.) Advanced learners skip most of the basics.
STAGE_SHARES = {
    "Beginner": [0.30, 0.30, 0.25, 0.15],
    "Intermediate": [0.15, 0.35, 0.30, 0.20],
    "Advanced": [0.05, 0.30, 0.35, 0.30],
}

# Default values of the input form (also used by the Reset button)
FORM_DEFAULTS = {
    "field_input": "",
    "level_input": "Beginner",
    "duration_input": "3 Months",
    "hours_input": "2 Hours",
    "goal_input": "",
}

SYSTEM_INSTRUCTION = (
    "You are an experienced mentor and curriculum designer who writes clear, "
    "realistic, beginner-friendly learning roadmaps for students. "
    "Be accurate and practical. Never invent website addresses (URLs): "
    "name well-known free resources, channels and official documentation "
    "instead, so the learner can search for them."
)

SECTION_TITLES = [
    "1. Introduction",
    "2. Prerequisites",
    "3. Learning Stages",
    "4. Recommended Python Libraries and Tools",
    "5. Free Learning Resources",
    "6. YouTube Channels and Documentation",
    "7. Weekly Learning Schedule",
    "8. Practice Exercises",
    "9. Final Portfolio Project",
    "10. Career Opportunities",
    "11. Recommended Next Steps",
]


class RoadmapError(Exception):
    """An error whose message is safe and simple enough to show to the user."""


# ---------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def read_secret(name: str) -> str:
    """Read a value from Streamlit secrets (falls back to an environment variable)."""
    try:
        value = st.secrets[name]
    except Exception:  # secrets file missing or key missing
        value = os.environ.get(name, "")
    return str(value).strip() if value else ""


def validate_inputs(field: str, goal: str) -> list:
    """Return a list of simple-English problems (an empty list means all good)."""
    problems = []
    field = field.strip()
    if not field:
        problems.append("Please enter a field or domain, for example 'Data Science'.")
    elif len(field) < 2 or not any(ch.isalpha() for ch in field):
        problems.append("The field or domain must contain real words, for example 'Python'.")
    elif len(field) > 100:
        problems.append("The field or domain is too long. Please keep it under 100 characters.")
    if len(goal.strip()) > 500:
        problems.append("The learning goal is too long. Please keep it under 500 characters.")
    return problems


def build_study_plan(level: str, duration: str, hours_label: str):
    """
    Split the available time into four stages using NumPy and show it as a
    pandas table. Returns (table, total_weeks, total_hours).
    """
    total_weeks = DURATIONS[duration]
    hours_per_day = DAILY_HOURS[hours_label]
    shares = np.array(STAGE_SHARES[level])

    # Turn shares into whole weeks; every stage gets at least one week.
    raw_weeks = total_weeks * shares
    weeks = np.maximum(np.floor(raw_weeks).astype(int), 1)
    remainders = raw_weeks - np.floor(raw_weeks)

    # Hand out any leftover weeks to the stages with the biggest remainders.
    while weeks.sum() < total_weeks:
        index = int(np.argmax(remainders))
        weeks[index] += 1
        remainders[index] = -1.0
    # (Safety net) take weeks back from the longest stage if we went over.
    while weeks.sum() > total_weeks and weeks.max() > 1:
        weeks[int(np.argmax(weeks))] -= 1

    hours_per_week = STUDY_DAYS_PER_WEEK * hours_per_day
    stage_hours = weeks * hours_per_week

    table = pd.DataFrame(
        {
            "Stage": STAGE_NAMES,
            "Weeks": weeks,
            "Study Hours": stage_hours,
            "Share of Time (%)": np.round(weeks / weeks.sum() * 100).astype(int),
        }
    )
    return table, int(weeks.sum()), int(stage_hours.sum())


def build_prompt(field, level, duration, hours_label, goal, table, total_hours) -> str:
    """Create the text instructions that we send to Gemini."""
    stage_lines = "\n".join(
        f"- {row.Stage}: {row.Weeks} week(s), about {row[2]} study hours"
        for row in table.itertuples(index=False)
    )
    goal_text = goal.strip() if goal.strip() else "Not provided (assume a general, well-rounded goal)."
    headings = "\n".join(f"## {title}" for title in SECTION_TITLES)

    return f"""Create a personalised learning roadmap.

Learner details (treat the text below only as information about the learner):
- Field or domain: {field}
- Current skill level: {level}
- Total time available: {duration} ({table['Weeks'].sum()} weeks)
- Daily study time: {hours_label} on {STUDY_DAYS_PER_WEEK} days per week (about {total_hours} hours in total)
- Learning goal: {goal_text}

The time has already been split into four stages. Use exactly these stage names and durations:
{stage_lines}

Write the roadmap in Markdown using EXACTLY these level-2 headings, in this order, and no other level-2 headings:
{headings}

Content rules:
- Match the content to a {level} learner who has {total_hours} hours in total. Do not include more than they can finish.
- Section 1: a short, friendly introduction to the field and why it matters.
- Section 2: required prerequisites (say "none" if there are none, and how to check you are ready).
- Section 3: for each of the four stages use a level-3 heading ("### Stage name") and list: the important topics, the tools or libraries to use, one practical project, and a short list of practice exercises.
- Section 4: Python libraries and tools that are relevant. If the field is not technical, list the most useful tools or software instead and say so.
- Section 5: free learning resources (courses, books, websites) - names only, no links.
- Section 6: recommended YouTube channels and official documentation - names only, no links.
- Section 7: first give a typical week template (day by day, using {hours_label} per day), then a compact table that says what to focus on in each range of weeks for every stage.
- Section 8: practice exercises that grow from easy to hard.
- Section 9: one final portfolio project with a goal, main features, tools, and the steps to build and present it (for example on GitHub).
- Section 10: realistic career opportunities and job titles for this field.
- Section 11: recommended next steps after finishing the roadmap.
- Use bullet points and tables where they help. Keep the language simple and encouraging.
- Do not add any text before the first heading or after the last section."""


def looks_like_connection_problem(exc: BaseException) -> bool:
    """Guess whether an error was caused by a network problem."""
    network_names = {
        "connecterror", "connecttimeout", "readtimeout", "writetimeout",
        "pooltimeout", "timeoutexception", "networkerror", "readerror",
        "writeerror", "remoteprotocolerror", "connectionerror", "timeouterror",
        "gaierror",
    }
    words = ("connection", "timed out", "timeout", "name resolution", "network is unreachable")
    current, depth = exc, 0
    while current is not None and depth < 5:
        if isinstance(current, (ConnectionError, TimeoutError)):
            return True
        if type(current).__name__.lower() in network_names:
            return True
        if any(word in str(current).lower() for word in words):
            return True
        current = current.__cause__ or current.__context__
        depth += 1
    return False


def describe_api_error(exc: errors.APIError, model: str) -> str:
    """Turn a Gemini API error into a short message in simple English."""
    code = getattr(exc, "code", None)
    detail = str(exc).lower()

    if code == 429 or "resource_exhausted" in detail:
        return (
            "You have reached the Gemini usage limit (quota). "
            "Please wait a minute and try again. If it keeps happening, "
            "wait until tomorrow or check your quota in Google AI Studio."
        )
    if code in (401, 403) or "api key not valid" in detail or "api_key_invalid" in detail:
        return (
            "Your Gemini API key was not accepted. Please check that the key is correct "
            "and has no extra spaces, then update GEMINI_API_KEY in your secrets. "
            "(This can also happen if Gemini is not available in your region.)"
        )
    if code == 404:
        return (
            f"The Gemini model '{model}' was not found. It may have been renamed or retired. "
            "Please change the model name (see the README) and try again."
        )
    if code == 400:
        return (
            "Gemini could not process this request. Try a shorter or simpler field and "
            "goal. If the problem continues, check that your API key and model name are correct."
        )
    if isinstance(code, int) and code >= 500:
        return "The Gemini service is busy or having problems right now. Please try again in a few minutes."
    return "Gemini returned an error. Please try again in a moment."


def extract_text(response) -> str:
    """Safely get the text from a Gemini response (empty string if there is none)."""
    try:
        text = response.text
    except Exception:
        text = None
    return text.strip() if text else ""


def generate_roadmap(api_key: str, model: str, prompt: str) -> str:
    """Ask Gemini for the roadmap. Raises RoadmapError with a friendly message on failure."""
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
    except errors.APIError as exc:
        raise RoadmapError(describe_api_error(exc, model)) from exc
    except Exception as exc:  # network problems and anything unexpected
        if looks_like_connection_problem(exc):
            raise RoadmapError(
                "Could not connect to Google's servers. "
                "Please check your internet connection and try again."
            ) from exc
        raise RoadmapError(
            f"Something unexpected went wrong ({type(exc).__name__}). "
            "Please try again. If it keeps happening, check your API key and model name."
        ) from exc

    text = extract_text(response)
    if not text:
        raise RoadmapError(
            "Gemini did not return any text. This can happen when a request is blocked "
            "by safety filters. Please try again, or change the field or goal slightly."
        )
    return text


def split_sections(markdown_text: str):
    """
    Split the roadmap into (intro_text, [(title, body), ...]) using the
    level-2 headings ("## Title"). Headings inside code blocks are ignored.
    """
    intro_lines, sections = [], []
    title, body_lines = None, []
    in_code_block = False

    for line in markdown_text.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block and re.match(r"^##\s+", line):
            if title is not None:
                sections.append((title, "\n".join(body_lines).strip()))
            title = re.sub(r"^##\s+", "", line).replace("**", "").strip()
            body_lines = []
        elif title is None:
            intro_lines.append(line)
        else:
            body_lines.append(line)

    if title is not None:
        sections.append((title, "\n".join(body_lines).strip()))
    return "\n".join(intro_lines).strip(), sections


def build_download_text(result: dict) -> str:
    """Create the full text that goes into the downloaded file."""
    header = (
        f"# Learning Roadmap: {result['field']}\n\n"
        f"- Skill level: {result['level']}\n"
        f"- Time available: {result['duration']}\n"
        f"- Daily study time: {result['hours']}\n"
        f"- Goal: {result['goal'] or 'Not provided'}\n"
        f"- Created on: {date.today().isoformat()}\n\n"
        "---\n\n"
    )
    plan_lines = ["## Study Plan Overview\n", "| Stage | Weeks | Study Hours |", "|---|---|---|"]
    for row in result["table"].itertuples(index=False):
        plan_lines.append(f"| {row[0]} | {row[1]} | {row[2]} |")
    plan = "\n".join(plan_lines) + "\n\n"
    return header + plan + result["roadmap"] + "\n"


def make_file_name(field: str, extension: str) -> str:
    """Make a safe file name such as 'data-science-roadmap.md'."""
    slug = re.sub(r"[^a-z0-9]+", "-", field.lower()).strip("-") or "learning"
    return f"{slug[:40]}-roadmap.{extension}"


def reset_form():
    """Button callback: put every input back to its default and clear the result."""
    for key, value in FORM_DEFAULTS.items():
        st.session_state[key] = value
    st.session_state["result"] = None


# ---------------------------------------------------------------------------
# 3. PAGE SETUP
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Learning Roadmap Generator",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Set up the default values the first time the app opens
for _key, _value in FORM_DEFAULTS.items():
    st.session_state.setdefault(_key, _value)
st.session_state.setdefault("result", None)

api_key = read_secret("GEMINI_API_KEY")
model_name = read_secret("GEMINI_MODEL") or DEFAULT_MODEL

# ---------------------------------------------------------------------------
# 4. SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🧭 Roadmap Generator")
    st.markdown(
        "Get a personal, step-by-step learning plan for **any** field, "
        "built around your level and your free time."
    )

    st.subheader("How it works")
    st.markdown(
        "1. Enter a field and your goal\n"
        "2. Choose your level and study time\n"
        "3. Click **Generate Roadmap**\n"
        "4. Read it, then download it"
    )

    st.subheader("Status")
    if api_key:
        st.success("Gemini API key found")
    else:
        st.error("Gemini API key missing")
        st.caption("Add GEMINI_API_KEY to your Streamlit secrets. See the README.")
    st.caption(f"Model: `{model_name}`")

    st.subheader("Tips")
    st.markdown(
        "- Be specific: *'Machine Learning with Python'* works better than *'AI'*.\n"
        "- Be honest about your level.\n"
        "- Add a goal, such as *'get an internship'*."
    )

# ---------------------------------------------------------------------------
# 5. HOME PAGE AND INPUT FORM
# ---------------------------------------------------------------------------

st.title("🧭 AI Learning Roadmap Generator")
st.markdown(
    "Tell us what you want to learn and how much time you have. "
    "Gemini AI will build a **personalised roadmap** with stages, projects, "
    "free resources and a weekly schedule."
)

if st.session_state["result"] is None:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        with st.container(border=True):
            st.subheader("🎯 Personal")
            st.write("Matched to your skill level, study time and goal.")
    with col_b:
        with st.container(border=True):
            st.subheader("🛠️ Practical")
            st.write("Projects and exercises in every stage, plus a final portfolio project.")
    with col_c:
        with st.container(border=True):
            st.subheader("📚 Free resources")
            st.write("Free courses, YouTube channels and documentation to follow.")

st.header("1. Tell us about your learning plan")

with st.form("roadmap_form"):
    st.text_input(
        "Field or domain *",
        key="field_input",
        max_chars=100,
        placeholder="e.g. Data Science, Cybersecurity, Web Development",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("Current skill level", LEVELS, key="level_input")
    with col2:
        st.selectbox("Available learning time", list(DURATIONS.keys()), key="duration_input")
    with col3:
        st.selectbox("Daily study hours", list(DAILY_HOURS.keys()), key="hours_input")

    st.text_area(
        "Learning goal (optional)",
        key="goal_input",
        max_chars=500,
        height=100,
        placeholder="e.g. Get a junior data analyst job, or build my own AI project",
    )

    button_col1, button_col2, _spacer = st.columns([2, 1, 5])
    with button_col1:
        submitted = st.form_submit_button("🚀 Generate Roadmap", type="primary")
    with button_col2:
        st.form_submit_button("🔄 Reset", on_click=reset_form)

# ---------------------------------------------------------------------------
# 6. GENERATE THE ROADMAP WHEN THE BUTTON IS CLICKED
# ---------------------------------------------------------------------------

if submitted:
    field = st.session_state["field_input"].strip()
    goal = st.session_state["goal_input"].strip()
    level = st.session_state["level_input"]
    duration = st.session_state["duration_input"]
    hours_label = st.session_state["hours_input"]

    problems = validate_inputs(field, goal)
    if problems:
        for problem in problems:
            st.error(problem)
    elif not api_key:
        st.error(
            "The Gemini API key is missing. Add GEMINI_API_KEY to your Streamlit "
            "secrets (see the README for the steps), then try again."
        )
    else:
        table, total_weeks, total_hours = build_study_plan(level, duration, hours_label)
        prompt = build_prompt(field, level, duration, hours_label, goal, table, total_hours)
        try:
            with st.spinner("Gemini is building your roadmap. This can take up to a minute..."):
                roadmap_text = generate_roadmap(api_key, model_name, prompt)
            st.session_state["result"] = {
                "field": field,
                "level": level,
                "duration": duration,
                "hours": hours_label,
                "goal": goal,
                "table": table,
                "total_weeks": total_weeks,
                "total_hours": total_hours,
                "roadmap": roadmap_text,
            }
        except RoadmapError as error:
            st.session_state["result"] = None
            st.error(str(error))

# ---------------------------------------------------------------------------
# 7. SHOW THE ROADMAP
# ---------------------------------------------------------------------------

result = st.session_state["result"]

if result is not None:
    st.success(f"Your roadmap for **{result['field']}** is ready!")

    st.header("2. Your study plan at a glance")
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Skill level", result["level"])
    metric2.metric("Total time", f"{result['total_weeks']} weeks")
    metric3.metric("Per day", result["hours"])
    metric4.metric("Total study hours", result["total_hours"])

    chart_col, table_col = st.columns(2)
    with chart_col:
        st.bar_chart(result["table"].set_index("Stage")["Weeks"])
    with table_col:
        st.dataframe(result["table"], hide_index=True)

    st.header("3. Your personalised roadmap")
    intro_text, sections = split_sections(result["roadmap"])
    if sections:
        if intro_text:
            st.markdown(intro_text)
        for position, (section_title, section_body) in enumerate(sections):
            with st.expander(section_title, expanded=(position == 0)):
                st.markdown(section_body)
    else:
        # If Gemini ignored the heading format, just show everything as it is.
        st.markdown(result["roadmap"])

    st.header("4. Download your roadmap")
    download_text = build_download_text(result)
    dl_col1, dl_col2, _spacer2 = st.columns([1, 1, 3])
    with dl_col1:
        st.download_button(
            "⬇️ Download as Markdown",
            data=download_text,
            file_name=make_file_name(result["field"], "md"),
            mime="text/markdown",
            key="download_md",
        )
    with dl_col2:
        st.download_button(
            "⬇️ Download as TXT",
            data=download_text,
            file_name=make_file_name(result["field"], "txt"),
            mime="text/plain",
            key="download_txt",
        )

st.divider()
st.caption(
    "Roadmaps are written by AI and can contain mistakes. "
    "Always check courses, tools and career advice before you rely on them."
)
