from flask import Blueprint, render_template, jsonify, current_app, session, redirect, url_for
from db import get_connection

main_bp = Blueprint("main", __name__)

@main_bp.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))

    return redirect(url_for("auth.login_page"))

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

@main_bp.route("/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))

    return render_template("dashboard.html")

@main_bp.route("/leave", methods=["GET"])
def leave_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login_page"))

    return render_template("leave.html")