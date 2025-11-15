import streamlit as st
import json
import datetime
import requests
import base64
import plotly.express as px

# ------------------- Dark Mode aktivieren -------------------
st.set_page_config(page_title="Lernplan Dashboard", layout="wide")
st.markdown("""
    <style>
        body {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stApp {
            background-color: #0e1117;
        }
        h1, h2, h3, h4, h5, h6, p, label {
            color: #fafafa !important;
        }
        .css-1d391kg, .css-1v3fvcr {
            background-color: #262730 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ------------------- GitHub Secrets -------------------
GITHUB_TOKEN = st.secrets["github"]["token"]
REPO = st.secrets["github"]["repo"]
FILE_PATH = st.secrets["github"]["path"]
API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# ------------------- Funktionen für GitHub -------------------
def load_data_from_github():
    response = requests.get(API_URL, headers=HEADERS)
    if response.status_code == 200:
        content = response.json()["content"]
        decoded = base64.b64decode(content).decode("utf-8")
        return json.loads(decoded)
    else:
        return {
            "tasks": [],
            "weekly_plan": [],
            "exam": {"date": "", "chapters": []},
            "points": 0,
            "last_update": str(datetime.date.today())
        }

def save_data_to_github(data):
    get_resp = requests.get(API_URL, headers=HEADERS)
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

    encoded_content = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
    payload = {
        "message": "Update Lernplan Dashboard",
        "content": encoded_content,
        "sha": sha
    }
    requests.put(API_URL, headers=HEADERS, json=payload)

# ------------------- Session State initialisieren -------------------
if "data" not in st.session_state:
    st.session_state["data"] = load_data_from_github()

data = st.session_state["data"]

# Reset für neuen Tag
if data["last_update"] != str(datetime.date.today()):
    data["last_update"] = str(datetime.date.today())
    save_data_to_github(data)

# ------------------- Layout -------------------
st.title("📚 Lernplan Dashboard – All-in-One")
st.write("Tagesfortschritt, Wochenplaner, Klausurvorbereitung – mobil und cloud-ready!")

col1, col2 = st.columns([1, 1])

# ------------------- Bereich 1: Tagesfortschritt -------------------
with col1:
    st.subheader("Tagesfortschritt")

    # Formular für manuelle Tagesaufgaben
    with st.form("add_task"):
        task_name = st.text_input("Tagesaufgabe")
        task_duration = st.number_input("Dauer (h)", min_value=0.5, step=0.5)
        add_task_btn = st.form_submit_button("Hinzufügen")
        if add_task_btn and task_name:
            data["tasks"].append({"name": task_name, "duration": task_duration, "done": False})
            save_data_to_github(data)
            st.success("Tagesaufgabe hinzugefügt!")

    # Checkboxen für Tagesaufgaben (direkte Zuweisung)
    if data["tasks"]:
        st.write("### Tagesaufgaben")
        for idx, task in enumerate(data["tasks"]):
            data["tasks"][idx]["done"] = st.checkbox(
                f"{task['name']} ({task['duration']}h)",
                value=task["done"],
                key=f"task_{idx}"
            )

    # Berechnung: heutige Aufgaben aus Wochenplaner + manuelle Aufgaben
    today_en = datetime.date.today().strftime("%A")
    mapping = {
        "Monday": "Montag",
        "Tuesday": "Dienstag",
        "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag",
        "Friday": "Freitag",
        "Saturday": "Samstag",
        "Sunday": "Sonntag"
    }
    today = mapping.get(today_en, today_en)

    weekly_today = [wp for wp in data["weekly_plan"] if wp["day"] == today]

    total_duration = sum(task["duration"] for task in data["tasks"]) + sum(wp["duration"] for wp in weekly_today)
    completed_duration = (
        sum(task["duration"] for task in data["tasks"] if task["done"]) +
        sum(wp["duration"] for wp in weekly_today if wp.get("done"))
    )

    progress_ratio = completed_duration / total_duration if total_duration > 0 else 0

    # Diagramm anzeigen (auch wenn leer)
    if total_duration > 0:
        fig = px.pie(
            names=["Erledigt", "Offen"],
            values=[completed_duration, max(total_duration - completed_duration, 0)],
            title="Tagesfortschritt",
            color_discrete_sequence=["#00cc96", "#ef553b"]
        )
    else:
        fig = px.pie(
            names=["Keine Daten"],
            values=[1],
            title="Tagesfortschritt (Keine Aufgaben)",
            color_discrete_sequence=["#636EFA"]
        )

    st.plotly_chart(fig, use_container_width=True)
    st.progress(progress_ratio)
    st.write(f"✅ Erledigt: {completed_duration}h / 🎯 Ziel: {total_duration}h")

    # Speichern nach jeder Änderung
    save_data_to_github(data)

# ------------------- Bereich 2: Wochenplaner -------------------
with col2:
    st.subheader("Wochenplaner")
    with st.form("add_weekly_task"):
        day = st.selectbox("Tag", ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"])
        activity = st.text_input("Lerntätigkeit")
        duration = st.number_input("Geplante Dauer (h)", min_value=0.5, step=0.5)
        submitted = st.form_submit_button("Hinzufügen")
        if submitted and activity:
            data["weekly_plan"].append({"day": day, "activity": activity, "duration": duration, "done": False})
            save_data_to_github(data)
            st.success("Aktivität hinzugefügt!")

    if data["weekly_plan"]:
        st.write("### Wochenplan")
        for idx, wp in enumerate(data["weekly_plan"]):
            data["weekly_plan"][idx]["done"] = st.checkbox(
                f"{wp['day']}: {wp['activity']} ({wp['duration']}h)",
                value=wp["done"],
                key=f"wp_{idx}"
            )

    weekly_total = sum(wp["duration"] for wp in data["weekly_plan"])
    weekly_completed = sum(wp["duration"] for wp in data["weekly_plan"] if wp.get("done"))
    st.write(f"📅 Woche: {weekly_completed}h von {weekly_total}h")
    st.progress(weekly_completed / weekly_total if weekly_total > 0 else 0)

    # Speichern nach jeder Änderung
    save_data_to_github(data)

# ------------------- Bereich 3: Klausurfortschritt -------------------
st.subheader("Klausurfortschritt")
with st.form("exam_setup"):
    exam_date = st.date_input("Klausurdatum", value=datetime.date.today())
    chapters_count = st.number_input("Anzahl Kapitel", min_value=1, step=1)
    setup_submitted = st.form_submit_button("Speichern")
    if setup_submitted:
        data["exam"]["date"] = str(exam_date)
        if not data["exam"]["chapters"] or len(data["exam"]["chapters"]) != chapters_count:
            data["exam"]["chapters"] = [{"name": f"Kapitel {i+1}", "steps": [False]*6} for i in range(chapters_count)]
        save_data_to_github(data)
        st.success("Klausurinformationen gespeichert!")

if data["exam"]["date"]:
    days_left = (datetime.datetime.strptime(data["exam"]["date"], "%Y-%m-%d").date() - datetime.date.today()).days
    st.write(f"📅 Noch {days_left} Tage bis zur Klausur")

    total_steps = len(data["exam"]["chapters"]) * 6
    completed_steps = sum(sum(1 for step in chap["steps"] if step) for chap in data["exam"]["chapters"])
    progress = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
    st.progress(progress / 100)
    st.write(f"Fortschritt: {progress:.1f}%")

    for idx, chap in enumerate(data["exam"]["chapters"]):
        st.write(f"**{chap['name']}**")
        cols = st.columns(6)
        step_labels = ["Lesen", "Fragen", "25%", "50%", "75%", "100%"]
        for i in range(6):
            with cols[i]:
                data["exam"]["chapters"][idx]["steps"][i] = st.checkbox(
                    step_labels[i],
                    value=chap["steps"][i],
                    key=f"chap_{idx}_step_{i}"
                )

    save_data_to_github(data)

st.write("✅ Änderungen werden automatisch in GitHub gespeichert.")
