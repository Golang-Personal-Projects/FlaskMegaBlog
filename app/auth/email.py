from flask import render_template, current_app
from app.email import sendmail


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    sendmail("[Microblog] Reset Your Password",
             sender=current_app.config["ADMINS"][0],
             recipients=[user.email],
             html_body=render_template("email/reset_password.html", user=user, token=token)
             )
