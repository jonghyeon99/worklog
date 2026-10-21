import re
from flask import Blueprint, request, jsonify, render_template, current_app, session
from psycopg.errors import UniqueViolation
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection

auth_bp = Blueprint("auth", __name__)

def validate_password(password):
    if not 8 <= len(password) <= 128:
        return "パスワードは8〜128文字で入力してください。"

    if any(char.isspace() for char in password):
        return "パスワードに空白は使用できません。"

    has_letter = bool(re.search(r"[A-Za-z]", password))
    has_number = bool(re.search(r"[0-9]", password))
    has_symbol = bool(re.search(r"[^A-Za-z0-9\s]", password))

    category_count = sum([
        has_letter,
        has_number,
        has_symbol
    ])

    if category_count < 2:
        return (
            "パスワードは英字・数字・記号のうち"
            "2種類以上を組み合わせてください。"
        )

    return None

@auth_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")

@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "リクエスト形式が正しくありません。"
        }), 400

    username = data.get("username")
    password = data.get("password")
    password_confirm = data.get("password_confirm")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "error": "ユーザー名とパスワードを入力してください。"
        }), 400

    username = username.strip()

    if not 3 <= len(username) <= 50:
        return jsonify({
            "error": "ユーザー名は3〜50文字で入力してください。"
        }), 400

    password_error = validate_password(password)

    if password_error:
        return jsonify({
            "error": password_error
        }), 400

    if password != password_confirm:
        return jsonify({
            "error": "パスワードが一致しません。"
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (username, password_hash)
                )

                user_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO user_settings (user_id)
                    VALUES (%s)
                    """,
                    (user_id,)
                )

        return jsonify({
            "message": "ユーザー登録が完了しました。"
        }), 201

    except UniqueViolation:
        return jsonify({
            "error": "このユーザー名は既に使用されています。"
        }), 409

    except Exception:
        current_app.logger.exception(
            "ユーザー登録処理でエラーが発生しました。"
        )

        return jsonify({
            "error": "登録処理中にエラーが発生しました。"
        }), 500

@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "リクエスト形式が正しくありません。"
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "error": "ユーザー名とパスワードを入力してください。"
        }), 400

    username = username.strip()

    if not username or not password:
        return jsonify({
            "error": "ユーザー名とパスワードを入力してください。"
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, password_hash
                    FROM USERS
                    WHERE username = %s
                    """,
                    (username,)
                )
                user = cur.fetchone()

        if user is None or not check_password_hash(user[1], password):
            return jsonify({
                "error": "ユーザー名またはパスワードが正しくありません。"
            }), 401

        session.clear()
        session["user_id"] = user[0]

        return jsonify({
            "message": "ログインしました。",
            "redirect": "/dashboard"
        }), 200

    except Exception:
        current_app.logger.exception("ログイン処理でエラーが発生しました。")
        return jsonify({
            "error": "ログイン処理中にエラーが発生しました。"
        }), 500

@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "message": "ログアウトしました。",
        "redirect": "/login"
    }), 200