"""Local Flask application with a fixed-identity user profile baseline."""

import os

from flask import Flask, Blueprint as FlaskBlueprint, redirect
from flask.views import MethodView
from flask_smorest import Api, Blueprint
from marshmallow import Schema, fields, validate
from swagger_ui_bundle import swagger_ui_path


class HealthSchema(Schema):
    status = fields.String(required=True)
    service = fields.String(required=True)


class EchoSchema(Schema):
    message = fields.String(required=True, validate=validate.Length(min=1, max=200))


def create_app(test_config=None):
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.from_mapping(
        API_TITLE="Make NUTN Better API",
        API_VERSION="0.1.0",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/",
        OPENAPI_JSON_PATH="openapi.json",
        OPENAPI_SWAGGER_UI_PATH="/docs",
        OPENAPI_SWAGGER_UI_URL="/swagger-assets/",
        MAX_CONTENT_LENGTH=1024 * 1024,
        DATABASE=os.environ.get("ME_DATABASE", os.path.join(app.instance_path, "profile.sqlite3")),
    )
    if test_config:
        app.config.update(test_config)

    # Serve documentation assets locally: no CDN or network needed after install.
    app.register_blueprint(FlaskBlueprint(
        "swagger_assets", __name__, static_folder=swagger_ui_path,
        static_url_path="/swagger-assets",
    ))
    api = Api(app)
    routes = Blueprint("development", __name__, url_prefix="/api",
                       description="環境確認用介面，不讀寫資料庫。")

    @routes.route("/health")
    class Health(MethodView):
        @routes.response(200, HealthSchema)
        def get(self):
            """確認後端服務正常。"""
            return {"status": "ok", "service": "Make_NUTN_Better"}

    @routes.route("/dev/echo")
    class Echo(MethodView):
        @routes.arguments(EchoSchema, example={"message": "測試 Flask API"})
        @routes.response(200, EchoSchema)
        def post(self, payload):
            """測試 JSON 輸入與驗證；不保存資料。

            缺少 message、型別錯誤或空字串時回傳 422。
            此介面僅供開發環境確認，不是正式業務 API。
            """
            return payload

    api.register_blueprint(routes)

    from . import db, profile
    db.init_app(app)
    api.register_blueprint(profile.routes)

    @app.get("/")
    def index():
        return redirect("/docs")

    return app
