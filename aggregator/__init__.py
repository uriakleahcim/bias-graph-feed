from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    # This service is intentionally API-only.  Keep Flask from discovering or
    # serving a conventional static/template presentation layer by default.
    app = Flask(__name__, static_folder=None, template_folder=None)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY environment variable must be set (see .env.sample)"
        )
    app.config["SECRET_KEY"] = secret_key

    from aggregator.display_time import configured_timezone_name
    app.config["DISPLAY_TIMEZONE"] = configured_timezone_name()

    # Off by default: every page needs an account. On: signed-out visitors can
    # read Headlines, story pages and article summaries (aggregator/permissions.py).
    from aggregator.permissions import public_read_access_from_env
    app.config["PUBLIC_READ_ACCESS"] = public_read_access_from_env()

    db.init_app(app)
    migrate.init_app(app, db)

    from aggregator.blueprints.api import api
    app.register_blueprint(api)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def api_error(error):
        from flask import jsonify
        return jsonify({"error": error.name, "message": error.description}), error.code

    return app


def create_db(app):
    with app.app_context():
        db.session.execute(db.text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.session.commit()
        db.create_all()
