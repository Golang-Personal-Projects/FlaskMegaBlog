from urllib.parse import urlsplit
from flask_login import current_user, login_user, logout_user
from flask import render_template, flash, url_for, request
from sqlalchemy import select
from werkzeug.utils import redirect
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app import db
from app.models import User, Post
from app.auth.email import send_password_reset_email
from app.auth import bp

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("auth.login"))
        login_user(user=user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("main.index")
        flash("Login requested for user {}, remember_me={}".format(
            form.username.data, form.remember_me.data
        ))
        return redirect(next_page)
    return render_template("auth/login.html", title="Sign In", form=form)

@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))

@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you have been registered!!!")
        return redirect(url_for("main.index"))
    return render_template("auth/register.html", title="Register", form=form)


@bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)

@bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.verify_reset_password(token=token)

    if not user:
        return redirect(url_for("main.index"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset.")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)

