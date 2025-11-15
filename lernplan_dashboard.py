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
        body { background-color: #0e1117; color: #fafafa; }
        .stApp { background-color: #0e1117; }
        h1, h2, h3, h4, h5, h6, p, label { color: #fafafa !important; }
        .css-1d391kg, .css-1v3fvcr { background-color: #262730 !important; }
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
        return {"tasks": [], "weekly_plan": [], "exam": {"date": "", "chapters": []}, "last_update": str(datetime.date.today())}

def save_data_to_github(data):
    get_resp = requests.get(API_URL, headers=HEADERS)
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
    encoded_content = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
    payload = {"message": "Update Lernplan Dashboard", "content": encoded_content, "sha": sha}
    requests.put(API_URL, headers=HEADERS, json=payload)

# ------------------- Session State initialisieren -------------------
if "data" not in st.session_state:
    st.session_state["data"] = load_data_from_github()

data = st.session_state["data"]

# ------------------- Layout -------------------
st.title("📚 Lernplan Dashboard – All-in-One")
st.write("Tagesfortschritt, Wochenplaner, Klausurvorbereitung – mobil und cloud-ready!")

col1, col2 = st.columns([1, 1])

# ------------------- Bereich 1: Tagesfortschritt -------------------
with col1:
    st.subheader("Tagesfortschritt")

    # Neue Aufgabe hinzufügen
    with st.form("add_task"):
        task_name = st.text_input("Tagesaufgabe")
        task_duration = st.number_input("Dauer (h)", min_value=0.5, step=0.5)
        add_task_btn = st.form_submit_button("Hinzufügen")
        if add_task_btn and task_name:
            data["tasks"].append({"name": task_name, "duration": task_duration, "done": False})
            st.success("Tagesaufgabe hinzugefügt!")

    # Checkboxen für Tagesaufgaben
    if data["tasks"]:
        st.write("### Tagesaufgaben")
        for idx, task in enumerate(data["tasks"]):
            st.session_state["data"]["tasks"][idx]["done"] = st.checkbox(
                f"{task['name']} ({task['duration']}h)",
                value=task["done"],
                key=f"task_{idx}"
            )

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
            st.success("Aktivität hinzugefügt!")

    if data["weekly_plan"]:
        st.write("### Wochenplan")
        for idx, wp in enumerate(data["weekly_plan"]):
            st.session_state["data"]["weekly_plan"][idx]["done"] = st.checkbox(
                f"{wp['day']}: {wp['activity']} ({wp['duration']}h)",
                value=wp["done"],
                key=f"wp_{idx}"
            )

# ------------------- Fortschritt berechnen (nach allen Updates) -------------------
today_en = datetime.date.today().strftime("%A")
mapping = {"Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch", "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag"}
today = mapping.get(today_en, today_en)
weekly_today = [wp for wp in data["weekly_plan"] if wp["day"] == today]

total_duration = sum(t["duration"] for t in data["tasks"]) + sum(wp["duration"] for wp in weekly_today)
completed_duration = sum(t["duration"] for t in data["tasks"] if t["done"]) + sum(wp["duration"] for wp in weekly_today if wp["done"])
progress_ratio = completed_duration / total_duration if total_duration > 0 else 0

# Donut-Chart mit Prozentanzeige
if total_duration > 0:
    fig = px.pie(
        names=["Erledigt", "Offen"],
        values=[completed_duration, max(total_duration - completed_duration, 0)],
        hole=0.5,
        title=f"Tagesfortschritt ({progress_ratio*100:.0f}%)",
        color_discrete_sequence=["#00cc96", "#ef553b"]
    )
else:
    fig = px.pie(names=["Keine Daten"], values=[1], hole=0.5, title="Tagesfortschritt (Keine Aufgaben)", color_discrete_sequence=["#636EFA"])
st.plotly_chart(fig, use_container_width=True)
st.progress(progress_ratio)
st.write(f"✅ Erledigt: {completed_duration}h / 🎯 Ziel: {total_duration}h")

# ------------------- Speichern-Button -------------------
if st.button("💾 Änderungen in GitHub speichern"):
    save_data_to_github(data)
    st.success("Alle Änderungen wurden gespeichert!")
