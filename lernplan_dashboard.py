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
        .delete-btn { color: #ef553b; font-weight: bold; }
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
        return {"tasks": [], "weekly_plan": [], "exam": {"name": "", "date": "", "chapters": []}, "last_update": str(datetime.date.today())}

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

# ------------------- Tagesfortschritt berechnen -------------------
today_en = datetime.date.today().strftime("%A")
mapping = {"Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch", "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag"}
today = mapping.get(today_en, today_en)
weekly_today = [wp for wp in data["weekly_plan"] if wp["day"] == today]

total_duration = sum(t["duration"] for t in data["tasks"]) + sum(wp["duration"] for wp in weekly_today)
completed_duration = sum(t["duration"] for t in data["tasks"] if t["done"]) + sum(wp["duration"] for wp in weekly_today if wp["done"])
progress_ratio = completed_duration / total_duration if total_duration > 0 else 0

# ------------------- Klausurfortschritt berechnen -------------------
days_left = (datetime.datetime.strptime(data["exam"]["date"], "%Y-%m-%d").date() - datetime.date.today()).days if data["exam"]["date"] else 0
total_steps = len(data["exam"]["chapters"]) * 6
completed_steps = sum(sum(1 for step in chap["steps"] if step) for chap in data["exam"]["chapters"])
progress_exam = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
steps_left = total_steps - completed_steps
daily_target = steps_left / days_left if days_left > 0 else steps_left

# ------------------- Diagramme nebeneinander -------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📅 Tagesfortschritt")
    if total_duration > 0:
        fig_day = px.pie(names=["Erledigt", "Offen"], values=[completed_duration, max(total_duration - completed_duration, 0)],
                         hole=0.5, title=f"{progress_ratio*100:.0f}%", color_discrete_sequence=["#00cc96", "#ef553b"])
    else:
        fig_day = px.pie(names=["Keine Daten"], values=[1], hole=0.5, title="Keine Aufgaben", color_discrete_sequence=["#636EFA"])
    st.plotly_chart(fig_day, use_container_width=True)
    st.progress(progress_ratio)
    st.write(f"✅ {completed_duration}h / 🎯 {total_duration}h")

with col_right:
    st.subheader("📚 Klausurfortschritt")
    if total_steps > 0:
        fig_exam = px.pie(names=["Erledigt", "Offen"], values=[completed_steps, steps_left],
                          hole=0.5, title=f"{progress_exam:.0f}%", color_discrete_sequence=["#00cc96", "#ef553b"])
    else:
        fig_exam = px.pie(names=["Keine Daten"], values=[1], hole=0.5, title="Keine Klausur", color_discrete_sequence=["#636EFA"])
    st.plotly_chart(fig_exam, use_container_width=True)
    st.progress(progress_exam / 100)
    st.write(f"✅ {completed_steps}/{total_steps} Schritte")

# ------------------- Warnung Soll/Ist -------------------
if days_left > 0 and steps_left > 0:
    if daily_target > 6:  # Beispiel: Warnung, wenn unrealistisch viel pro Tag
        st.error(f"⚠️ Du bist im Rückstand! Du müsstest **{daily_target:.1f} Schritte pro Tag** schaffen.")
    else:
        st.info(f"📈 Du musst **{daily_target:.1f} Schritte pro Tag** erledigen, um rechtzeitig fertig zu sein.")

# ------------------- Aufgabenverwaltung -------------------
st.subheader("Tagesaufgaben")
for idx, task in enumerate(data["tasks"]):
    col_task, col_del = st.columns([4, 1])
    with col_task:
        data["tasks"][idx]["done"] = st.checkbox(f"{task['name']} ({task['duration']}h)", value=task["done"], key=f"task_{idx}")
    with col_del:
        if st.button("🗑️", key=f"del_task_{idx}"):
            data["tasks"].pop(idx)
            st.experimental_rerun()

# ------------------- Klausurverwaltung -------------------
st.subheader("Klausurverwaltung")
with st.form("exam_setup"):
    exam_name = st.text_input("Name der Klausur", value=data["exam"].get("name", ""))
    exam_date = st.date_input("Klausurdatum", value=datetime.date.today() if not data["exam"]["date"] else datetime.datetime.strptime(data["exam"]["date"], "%Y-%m-%d").date())
    chapters_count = st.number_input("Anzahl Kapitel", min_value=1, step=1, value=len(data["exam"]["chapters"]) if data["exam"]["chapters"] else 1)
    setup_submitted = st.form_submit_button("Speichern")
    if setup_submitted:
        data["exam"]["name"] = exam_name
        data["exam"]["date"] = str(exam_date)
        if not data["exam"]["chapters"] or len(data["exam"]["chapters"]) != chapters_count:
            data["exam"]["chapters"] = [{"name": f"Kapitel {i+1}", "steps": [False]*6} for i in range(chapters_count)]
        save_data_to_github(data)
        st.success("Klausurinformationen gespeichert!")

# Kapitel-Checkboxen + Löschoption
step_labels = ["Lesen", "Fragen", "25%", "50%", "75%", "100%"]
for idx, chap in enumerate(data["exam"]["chapters"]):
    st.write(f"**{chap['name']}**")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            data["exam"]["chapters"][idx]["steps"][i] = st.checkbox(step_labels[i], value=chap["steps"][i], key=f"chap_{idx}_step_{i}")
    if st.button("Kapitel löschen", key=f"del_chap_{idx}"):
        data["exam"]["chapters"].pop(idx)
        st.experimental_rerun()

# Klausur komplett löschen
if st.button("❌ Klausur zurücksetzen"):
    data["exam"] = {"name": "", "date": "", "chapters": []}
    st.experimental_rerun()

# ------------------- Speichern-Button -------------------
if st.button("💾 Änderungen in GitHub speichern"):
    save_data_to_github(data)
    st.success("Alle Änderungen wurden gespeichert!")
