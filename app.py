import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from send_emails import send_email

st.set_page_config(page_title="Reporting Dashboard", layout="wide")

# ==== Load master report data ====
REPORT_PATH = "data/report.csv"
STATUS_PATH = "data/report_status.csv"

# Buat folder data kalau belum ada
os.makedirs("data", exist_ok=True)

# Baca master data
df_master = pd.read_csv(REPORT_PATH)

# Buat file status kalau belum ada
if not os.path.exists(STATUS_PATH):
    df_status = pd.DataFrame(columns=["Report Name", "Month", "Year", "Deadline", "Status", "Added By", "Added Date"])
    df_status.to_csv(STATUS_PATH, index=False)
else:
    df_status = pd.read_csv(STATUS_PATH)

# ==== Helper functions ====
def get_periodical_reports_for_month(month, year):
    """Generate all periodical reports that should appear in this month."""
    month_name = calendar.month_name[month]
    rows = []

    for _, row in df_master.iterrows():
        if row["Report Type"] == "Periodical":
            period = str(row["Report Period"]).lower()
            if "every month" in period or month_name.lower() in period:
                # Tentukan tanggal deadline
                if "last" in str(row["Deadline"]).lower():
                    day = calendar.monthrange(year, month)[1]
                else:
                    try:
                        day = int(''.join([c for c in str(row["Deadline"]) if c.isdigit()]))
                    except:
                        day = 15
                rows.append({
                    "Report Name": row["Report Name"],
                    "Month": month_name,
                    "Year": year,
                    "Deadline": datetime(year, month, day).strftime("%Y-%m-%d"),
                    "Status": "Not Started",
                    "Added By": "System",
                    "Added Date": datetime.now().strftime("%Y-%m-%d")
                })
    return pd.DataFrame(rows)

def merge_reports(month, year):
    """Gabungkan data periodical otomatis + status yang sudah disimpan"""
    auto = get_periodical_reports_for_month(month, year)
    existing = df_status[(df_status["Month"] == calendar.month_name[month]) & (df_status["Year"] == year)]
    merged = pd.concat([auto, existing]).drop_duplicates(subset=["Report Name", "Deadline"], keep="last").reset_index(drop=True)
    return merged

# ==== Tampilan Kalender ====
st.title("📅 Reporting Fulfillment Dashboard")

today = datetime.today()
month = st.session_state.get("month", today.month)
year = st.session_state.get("year", today.year)

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("← Prev Month"):
        if month == 1:
            month, year = 12, year - 1
        else:
            month -= 1
with col3:
    if st.button("Next Month →"):
        if month == 12:
            month, year = 1, year + 1
        else:
            month += 1

st.session_state["month"] = month
st.session_state["year"] = year

st.subheader(f"{calendar.month_name[month]} {year}")

cal = calendar.Calendar()
days = cal.monthdayscalendar(year, month)
df_current = merge_reports(month, year)

# Mapping status ke warna
def get_day_color(day):
    """Tentukan warna berdasarkan status report pada tanggal itu"""
    if day == 0:
        return No
    day_str = f"{year}-{month:02d}-{day:02d}"
    reports_today = df_current[df_current["Deadline"] == day_str]

    if len(reports_today) == 0:
        return "#2C2C2C"  # abu tua (tidak ada report)
    elif all(reports_today["Status"] == "Completed"):
        return "#388E3C"  # hijau tua
    elif any(reports_today["Status"] == "In Progress"):
        return "#FBC02D"  # kuning tua
    else:
        return "#D32F2F"  # merah tua

# ==== Render kalender berwarna + border biru di hari ini ====
st.markdown("### 🗓️ Calendar View")
today_date = datetime.today().date()

for week in days:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].empty()
        else:
            color = get_day_color(day)
            current_date = datetime(year, month, day).date()
            is_today = current_date == today_date

            # 🟦 Border biru tebal untuk hari ini
            border = "3px solid #2196F3" if is_today else "1px solid #555"

            cols[i].markdown(
                f"""
                <div style='
                    background-color:{color};
                    border:{border};
                    border-radius:8px;
                    padding:10px;
                    text-align:center;
                    color:white;
                    font-weight:600;
                    box-shadow:{'0 0 10px #2196F3' if is_today else 'none'};
                '>
                    {day}
                </div>
                """,
                unsafe_allow_html=True
            )

# Tambah legenda warna di bawah kalender
st.markdown("""
<div style='display:flex; gap:15px; margin-top:10px'>
  <div style='background-color:#D32F2F; width:20px; height:20px; border-radius:4px; display:inline-block'></div> Not Started
  <div style='background-color:#FBC02D; width:20px; height:20px; border-radius:4px; display:inline-block'></div> In Progress
  <div style='background-color:#388E3C; width:20px; height:20px; border-radius:4px; display:inline-block'></div> Completed
  <div style='background-color:#2C2C2C; width:20px; height:20px; border-radius:4px; display:inline-block'></div> No Report
</div>
""", unsafe_allow_html=True)



# ==== Inquiry Table ====
st.markdown("---")
st.subheader("📊 Report Inquiry Table")

df_current = merge_reports(month, year)

# Tampilkan tabel editable
edited_df = st.data_editor(
    df_current,
    use_container_width=True,
    key="table_edit",
    disabled=["Report Name", "Month", "Year", "Deadline", "Added By", "Added Date"],
    column_config={
        "Status": st.column_config.SelectboxColumn(options=["Not Started", "In Progress", "Completed"])
    },
)

# Tombol Save
if st.button("💾 Save Changes"):
    df_to_save = pd.concat([df_status, edited_df]).drop_duplicates(subset=["Report Name", "Deadline"], keep="last")
    df_to_save.to_csv(STATUS_PATH, index=False)
    st.success("Changes saved successfully!")
    st.rerun()

# ==== Form Tambah Incidental Report ====
st.markdown("---")
st.subheader("➕ Add Incidental Report")

incidental_reports = df_master[df_master["Report Type"] == "Incidental"]["Report Name"].tolist()
with st.form("add_incidental_form"):
    selected_report = st.selectbox("Select Report Name", incidental_reports)
    selected_deadline = st.date_input("Select Deadline", datetime.today())
    add_btn = st.form_submit_button("Add Report")

    if add_btn:
        new_entry = pd.DataFrame([{
            "Report Name": selected_report,
            "Month": calendar.month_name[selected_deadline.month],
            "Year": selected_deadline.year,
            "Deadline": selected_deadline.strftime("%Y-%m-%d"),
            "Status": "Not Started",
            "Added By": "User",
            "Added Date": datetime.now().strftime("%Y-%m-%d")
        }])
        df_status = pd.concat([df_status, new_entry], ignore_index=True)
        df_status.to_csv(STATUS_PATH, index=False)
        # === 🔔 Kirim Email Notifikasi ===
        receiver = "farrasthariq@gmail.com"  # ubah sesuai penerima kamu
        subject = f"New Incidental Report Added: {selected_report}"
        body = f"""
        <h3>📢 New Incidental Report Added</h3>
        <p><b>Report Name:</b> {selected_report}</p>
        <p><b>Deadline:</b> {selected_deadline.strftime('%Y-%m-%d')}</p>
        <p>This report has been added by user on {datetime.now().strftime('%Y-%m-%d')}.</p>
        """
        send_email_notification(receiver, subject, body)
        # === =============================
    
        st.success(f"✅ {selected_report} added for {selected_deadline.strftime('%B %Y')}!")
        st.rerun()
