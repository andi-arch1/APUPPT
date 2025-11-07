import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
from send_emails import send_email

st.set_page_config(page_title="Reporting Dashboard", layout="wide")

# ==== File paths ====
REPORT_PATH = "data/report.csv"
STATUS_PATH = "data/report_status.csv"

# Ensure folder exists
os.makedirs("data", exist_ok=True)

# ==== Load Master ====
df_master = pd.read_csv(REPORT_PATH, sep=';')

# ==== Init status file ====
if not os.path.exists(STATUS_PATH):
    df_status = pd.DataFrame(columns=[
        "Report Name", "Month", "Year", "From Date", "Deadline",
        "Status", "PIC", "Added By", "Added Date"
    ])
    df_status.to_csv(STATUS_PATH, index=False)
else:
    df_status = pd.read_csv(STATUS_PATH)

# ==== Helper: Generate periodical reports ====
def get_periodical_reports_for_month(month, year):
    month_name = calendar.month_name[month]
    rows = []

    for _, row in df_master.iterrows():
        if row["Report Type"] == "Periodical":
            period = str(row["Report Period"]).lower()
            if "every month" in period or month_name.lower() in period:
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
                    "From Date": datetime(year, month, 1).strftime("%Y-%m-%d"),  # always 1st
                    "Deadline": datetime(year, month, day).strftime("%Y-%m-%d"),
                    "Status": "Not Started",
                    "PIC": row.get("PIC", ""),
                    "Added By": "System",
                    "Added Date": datetime.now().strftime("%Y-%m-%d")
                })
    return pd.DataFrame(rows)

# ==== Merge ====
def merge_reports(month, year):
    auto = get_periodical_reports_for_month(month, year)
    existing = df_status[(df_status["Month"] == calendar.month_name[month]) & (df_status["Year"] == year)]
    merged = pd.concat([auto, existing]).drop_duplicates(subset=["Report Name", "Deadline"], keep="last").reset_index(drop=True)
    return merged

# ==== Calendar UI ====
st.title("📅 Reporting Fulfillment Dashboard")

today = datetime.today()
month = st.session_state.get("month", today.month)
year = st.session_state.get("year", today.year)

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("← Prev Month"):
        month, year = (12, year - 1) if month == 1 else (month - 1, year)
with col3:
    if st.button("Next Month →"):
        month, year = (1, year + 1) if month == 12 else (month + 1, year)

st.session_state["month"] = month
st.session_state["year"] = year

st.subheader(f"{calendar.month_name[month]} {year}")

cal = calendar.Calendar()
days = cal.monthdayscalendar(year, month)
df_current = merge_reports(month, year)

# ==== Color mapping ====
def get_day_color(day):
    """Color day based on report status and apply gradient intensity for 3 days before deadline."""
    if day == 0:
        return None

    day_str = f"{year}-{month:02d}-{day:02d}"
    current_date = datetime(year, month, day).date()
    base_color = "#2C2C2C"  # default gray (no report)

    for _, row in df_current.iterrows():
        deadline_date = datetime.strptime(row["Deadline"], "%Y-%m-%d").date()
        diff_days = (deadline_date - current_date).days

        if 0 <= diff_days <= 3:
            # pick base color based on status
            if row["Status"] == "Completed":
                base_hex = (56, 142, 60)   # green
            elif row["Status"] == "In Progress":
                base_hex = (251, 192, 45)  # yellow
            else:
                base_hex = (211, 47, 47)   # red

            # compute gradient intensity (closer → brighter)
            factor = 1 - (diff_days / 3)  # 0.0 → full bright, 1.0 → dim
            r = int(base_hex[0] + (255 - base_hex[0]) * (1 - factor))
            g = int(base_hex[1] + (255 - base_hex[1]) * (1 - factor))
            b = int(base_hex[2] + (255 - base_hex[2]) * (1 - factor))

            return f"rgb({r},{g},{b})"

    return base_color

# ==== Render calendar with blue border for today ====
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
            border = "3px solid #2196F3" if is_today else "1px solid #555"
            cols[i].markdown(f"""
                <div style='
                    background-color:{color};
                    border:{border};
                    border-radius:8px;
                    padding:10px;
                    text-align:center;
                    color:white;
                    font-weight:600;
                    box-shadow:{'0 0 10px #2196F3' if is_today else 'none'};
                '>{day}</div>
            """, unsafe_allow_html=True)

st.markdown("""
<div style='display:flex; gap:15px; margin-top:10px'>
  <div style='background-color:#D32F2F; width:20px; height:20px; border-radius:4px; display:inline-block'></div> Not Started
  <div style='background-color:#FBC02D; width:20px; height:20px; border-radius:4px; display:inline-block'></div> In Progress
  <div style='background-color:#388E3C; width:20px; height:20px; border-radius:4px; display:inline-block'></div> Completed
  <div style='background-color:#2C2C2C; width:20px; height:20px; border-radius:4px; display:inline-block'></div> No Report
</div>
""", unsafe_allow_html=True)

# ==== Table View ====
st.markdown("---")
st.subheader("📊 Report Inquiry Table")

df_current = merge_reports(month, year)

edited_df = st.data_editor(
    df_current,
    use_container_width=True,
    key="table_edit",
    disabled=["Report Name", "Month", "Year", "From Date", "Deadline", "Added By", "Added Date", "PIC"],
    column_config={
        "Status": st.column_config.SelectboxColumn(options=["Not Started", "In Progress", "Completed"])
    },
)

if st.button("💾 Save Changes"):
    df_to_save = pd.concat([df_status, edited_df]).drop_duplicates(subset=["Report Name", "Deadline"], keep="last")
    df_to_save.to_csv(STATUS_PATH, index=False)
    st.success("Changes saved successfully!")
    st.rerun()

# ==== Add Incidental Report ====
st.markdown("---")
st.subheader("➕ Add Incidental Report")

incidental_reports = df_master[df_master["Report Type"] == "Incidental"]["Report Name"].tolist()

with st.form("add_incidental_form"):
    selected_report = st.selectbox("Select Report Name", incidental_reports)
    selected_from = st.date_input("From Date (Email Received)", datetime.today())
    selected_deadline = st.date_input("Select Deadline", datetime.today())
    add_btn = st.form_submit_button("Add Report")

    if add_btn:
        pic_value = df_master.loc[df_master["Report Name"] == selected_report, "PIC"].values[0] if not df_master.empty else ""
        new_entry = pd.DataFrame([{
            "Report Name": selected_report,
            "Month": calendar.month_name[selected_deadline.month],
            "Year": selected_deadline.year,
            "From Date": selected_from.strftime("%Y-%m-%d"),
            "Deadline": selected_deadline.strftime("%Y-%m-%d"),
            "Status": "Not Started",
            "PIC": pic_value,
            "Added By": "User",
            "Added Date": datetime.now().strftime("%Y-%m-%d")
        }])
        df_status = pd.concat([df_status, new_entry], ignore_index=True)
        df_status.to_csv(STATUS_PATH, index=False)

        st.success(f"✅ {selected_report} added for {selected_deadline.strftime('%B %Y')}!")
        st.rerun()
