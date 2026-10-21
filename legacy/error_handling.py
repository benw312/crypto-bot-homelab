#error_handling.py
import os
import smtplib
from email.message import EmailMessage

# Email settings are read from the environment (see .env.example)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.environ["ALERT_EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["ALERT_EMAIL_PASSWORD"]
RECIPIENT_EMAIL = os.getenv("ALERT_RECIPIENT_EMAIL", EMAIL_ADDRESS)

# Subject and content for the error notification email
EMAIL_SUBJECT = "Error in your Cryptocurrency Data Collector"
EMAIL_CONTENT = "An error occurred while running your cryptocurrency data collector. Please check the logs for more details."


def send_email(subject, content):
    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


def handle_error(error):
    print(f"An error occurred: {error}")
    send_email(EMAIL_SUBJECT, EMAIL_CONTENT)


if __name__ == "__main__":
    try:
        # This block is just to simulate an error for testing purposes
        raise Exception("Test error")
    except Exception as e:
        handle_error(e)
        print("Test passed: handle_error")
