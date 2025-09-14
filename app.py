import streamlit as st
import requests
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="XI Class Admission API Monitor",
    page_icon="📢",
    layout="wide"
)

# --- API and App State Initialization ---
API_URL = "https://xiclassadmission.gov.bd/api/home/api/announcements"
CHECK_INTERVAL_SECONDS = 300 # 5 minutes

# Initialize session state variables if they don't exist
if 'monitoring' not in st.session_state:
    st.session_state.monitoring = False
if 'last_known_filename' not in st.session_state:
    st.session_state.last_known_filename = "23.txt"
if 'last_check_time' not in st.session_state:
    st.session_state.last_check_time = 0
if 'log' not in st.session_state:
    st.session_state.log = []

# --- Functions ---

def get_numeric_from_filename(filename):
    """Extracts the integer from a filename like '24.txt'."""
    numbers = re.findall(r'\d+', filename)
    return int(numbers[0]) if numbers else 0

def fetch_data(url):
    """Fetches data from the API."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.toast(f"Error fetching data: {e}", icon="🔥")
        return None

def send_email(subject, body, smtp_config):
    """Sends an email using the provided SMTP configuration."""
    msg = MIMEMultipart()
    msg['From'] = smtp_config['sender_email']
    msg['To'] = smtp_config['recipient_email']
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        # Using SMTP_SSL for port 465
        with smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port']) as server:
            server.login(smtp_config['sender_email'], smtp_config['password'])
            server.send_message(msg)
        st.toast(f"✅ Notification email sent to {smtp_config['recipient_email']}!", icon="📧")
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# --- UI Layout ---

st.title("📢 XI Class Admission Announcement Monitor")
st.markdown(f"This app monitors the admission API. Once started, it will run continuously and check for new notices every {int(CHECK_INTERVAL_SECONDS / 60)} minutes.")

# --- Sidebar for SMTP Configuration ---
with st.sidebar:
    st.header("📧 Email Notification Settings")
    st.info("Enter the recipient's email address to receive alerts.")
    
    # Hardcoded SMTP details
    smtp_server = "mail.technogia.xyz"
    smtp_port = 465
    sender_email = "notice@technogia.xyz"
    sender_password = "q(;B$wDj(!cmDfu#"

    # Only ask for the recipient's email
    recipient_email = st.text_input("Recipient Email Address", "recipient_email@example.com")

    smtp_config = {
        "server": smtp_server,
        "port": smtp_port,
        "sender_email": sender_email,
        "password": sender_password,
        "recipient_email": recipient_email
    }
    st.markdown("---")
    st.header("Monitoring Controls")
    
    # Start Monitoring Button
    if st.button("Start Monitoring", type="primary"):
        if not recipient_email or "@" not in recipient_email:
            st.warning("Please enter a valid recipient email address before starting.")
        else:
            st.session_state.monitoring = True
            st.session_state.last_check_time = 0 
            st.session_state.log.append(f"**[{datetime.now().strftime('%I:%M:%S %p')}]** Monitoring started.")
            st.rerun()

    # Stop Monitoring Button
    if st.button("Stop Monitoring"):
        st.session_state.monitoring = False
        st.session_state.log.append(f"**[{datetime.now().strftime('%I:%M:%S %p')}]** Monitoring stopped.")
        st.rerun()

    st.markdown("---")
    if st.button("Clear Log"):
        st.session_state.log = []
        st.rerun()


# --- Main Application Area ---
status_placeholder = st.empty()
last_updated_placeholder = st.empty()
countdown_placeholder = st.empty()
log_placeholder = st.container(height=300)

# Display the persistent log
with log_placeholder:
    for entry in reversed(st.session_state.log):
        st.markdown(entry)

if st.session_state.monitoring:
    status_placeholder.success(f"🟢 Monitoring is ACTIVE. Last known notice: `{st.session_state.last_known_filename}`")

    current_time = time.time()
    
    # Check if the interval has passed
    if current_time - st.session_state.last_check_time > CHECK_INTERVAL_SECONDS:
        st.session_state.last_check_time = current_time 
        
        data = fetch_data(API_URL)
        print("Api Has Been Called")

        if data and "announcements" in data and data["announcements"]:
            latest_announcement = data["announcements"][0]
            latest_filename = latest_announcement['filename']
            
            now_str = datetime.now().strftime('%I:%M:%S %p')
            
            last_known_num = get_numeric_from_filename(st.session_state.last_known_filename)
            latest_num = get_numeric_from_filename(latest_filename)

            if latest_num > last_known_num:
                log_entry = f"**[{now_str}]** :white_check_mark: **New Announcement Found!** Filename: `{latest_filename}`. Sending email."
                st.session_state.log.append(log_entry)
                
                email_subject = f"New XI Admission Announcement: {latest_filename}"
                email_body = f"""
                <html><body>
                    <h2>A new announcement has been posted on the XI Class Admission website.</h2>
                    <p><strong>Filename:</strong> {latest_announcement['filename']}</p><hr>
                    <p><strong>Content:</strong></p><div>{latest_announcement['content']}</div>
                </body></html>
                """
                send_email(email_subject, email_body, smtp_config)
                
                st.session_state.last_known_filename = latest_filename
                
            else:
                log_entry = f"**[{now_str}]** No new announcements. Current latest is still `{latest_filename}`."
                st.session_state.log.append(log_entry)
        
        # This will rerun the script to update the log immediately
        st.rerun()

    # --- Countdown Timer and continous loop trigger ---
    next_check_time = st.session_state.last_check_time + CHECK_INTERVAL_SECONDS
    time_left = max(0, int(next_check_time - time.time()))
    mins, secs = divmod(time_left, 60)
    countdown_placeholder.metric("Next Check In", f"{mins:02d}:{secs:02d}")
    
    # This keeps the script running and a live countdown
    time.sleep(1)
    st.rerun()

else:
    status_placeholder.error("🔴 Monitoring is STOPPED. Click 'Start Monitoring' in the sidebar to begin.")
    countdown_placeholder.empty()

