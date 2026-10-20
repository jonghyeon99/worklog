from flask import Blueprint, render_template, jsonify, current_app
from db import get_connection

main_bp = Blueprint("main", __name__)

@main_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@main_bp.route("/api/health", methods=["GET"])
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        return jsonify({
            "status": "ok",
            "database": "connected"
        }), 200

    except Exception:
        current_app.logger.exception(
            "データベース接続確認中にエラーが発生しました。"
        )

        return jsonify({
            "status": "error",
            "database": "unavailable"
        }), 503
