import smtplib
from email.mime.text import MIMEText
from datetime import datetime

def send_email_notification(receiver_email, subject, body):
    from dotenv import load_dotenv
    import os

    load_dotenv()
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")

    msg = MIMEText(body, "html")
    msg["Subject"] = Testing Notification
    msg["From"] = sender_email
    msg["To"] = receiver_email

    with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

    print(f"✅ Email sent to {receiver_email}")
