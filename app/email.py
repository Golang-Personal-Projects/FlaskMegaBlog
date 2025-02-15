from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app import mail
from threading import Thread
from flask_mail import Message
import app


def sendmail(subject, sender, recipients, html_body, attachments=None, sync=False):
    message = Mail(
        from_email=sender,
        to_emails=recipients,
        subject=subject,
        html_content=html_body)
    if attachments:
        for attachment in attachments:
            message.add_attachment(attachment=attachment)
    if sync:
        try:
            sg = SendGridAPIClient(api_key=current_app.config["SENDGRID_API_KEY"])
            response = sg.send(message)
            print(response.status_code)
            print(response.body)
            print(response.headers)
        except Exception as e:
            print(f"error: {e}")
    else:
        Thread(target=send_async_email, args=(app, message)).start()


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)
