from app import db
from flask import  render_template


def error_routes(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404


    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        return render_template("500.html"), 500