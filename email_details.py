import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(receiver_email, otp):
    sender_email = "anika.salsabil1@g.bracu.ac.bd"
    sender_password = "xnpy tdly zkdf eqkl"

    subject = "BnBeasy Email Verification OTP"
    body = f"""
Your OTP for BnBeasy registration is: {otp}

This OTP will expire in 5 minutes.
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    print(f"Attempting to send OTP email to {receiver_email}...")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise e

def send_booking_confirmation(receiver_email, booking_details):
    sender_email = "anika.salsabil1@g.bracu.ac.bd"
    sender_password = "xnpy tdly zkdf eqkl"

    subject = f"Booking Confirmation: {booking_details['listing_title']}"
    body = f"""
Hello,

Your booking for '{booking_details['listing_title']}' has been confirmed!

Details:
- Check-in: {booking_details['check_in']}
- Check-out: {booking_details['check_out']}
- Total Price: ${booking_details['total_price']}
- Note: {booking_details.get('note', 'N/A')}

Thank you for choosing BnBeasy!
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    print(f"Attempting to send booking confirmation to {receiver_email}...")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("Booking confirmation email sent.")
    except Exception as e:
        print(f"Failed to send booking confirmation email: {e}")
  
