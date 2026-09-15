import os
from flask import Flask, send_from_directory
from app.config import Config
from app.db import close_db
from app.metrics import init_metrics
from app.routes.api_routes import api_bp

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(api_bp, url_prefix="/api")

    app.teardown_appcontext(close_db)

    init_metrics(app)

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "login.html")

    @app.route("/<path:filename>")
    def serve_frontend(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    return app
