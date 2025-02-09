import os.path
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from config import Config
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask_mail import Mail
from flask_moment import Moment

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login = LoginManager()
mail = Mail()
moment = Moment()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database
    db.init_app(app=app)

    # Initialize Migration
    migrate.init_app(app=app, db=db)

    # Initialize Login
    login.init_app(app=app)
    login.login_view = "auth.login"

    # Initialize mail
    mail.init_app(app=app)

    # Initialize moment
    moment.init_app(app=app)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    if not app.debug and not app.testing:
        if app.config["MAIL_SERVER"]:
            auth = None
            if app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"]:
                auth = (app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"])
            secure = None
            if app.config["MAIL_USER_TLS"]:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]),
                fromaddr="noreply@" + app.config["MAIL_SERVER"],
                toaddrs=app.config["ADMINS"], subject="Blog Log Failures",
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        if not os.path.exists("logs"):
            os.mkdir("logs")
        filehandler = RotatingFileHandler("logs/blog.log", maxBytes=10240, backupCount=10)
        filehandler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"))
        filehandler.setLevel(logging.INFO)
        app.logger.addHandler(filehandler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("Blog startup")

    return app


from app import models
