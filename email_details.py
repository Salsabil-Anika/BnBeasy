import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(receiver_email, otp):
    subject = "BnBeasy Email Verification OTP"
    body = f"""
Your OTP for BnBeasy registration is: {otp}

This OTP will expire in 5 minutes.
"""
    send_email(receiver_email, subject, body)

def send_email(receiver_email, subject, body):
    sender_email = "anika.salsabil1@g.bracu.ac.bd"
    sender_password = "drlc tmzp ojmz xasx"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
