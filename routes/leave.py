from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, session, current_app
from db import get_connection

leave_bp = Blueprint("leave", __name__)

@leave_bp.route("/api/leave/grants", methods=["POST"])
def create_leave_grant():
    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "error": "ログインが必要です。"
        }), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "入力データが正しくありません。"
        }), 400

    try:
        granted_date = date.fromisoformat(data["granted_date"])
        expires_date = date.fromisoformat(data["expires_date"])
        granted_days = Decimal(str(data["granted_days"]))

    except (KeyError, TypeError, ValueError, InvalidOperation):
        return jsonify({
            "error": "入力内容を確認してください。"
        }), 400

    if expires_date < granted_date:
        return jsonify({
            "error": "有効期限は付与日以降に設定してください。"
        }), 400

    if (not granted_days.is_finite() or granted_days <= 0 or granted_days > 999 
        or granted_days * 2 != (granted_days * 2).to_integral_value()):
        return jsonify({
            "error": "付与日数は0.5日単位で入力してください。"
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO leave_grants (
                        user_id,
                        granted_date,
                        granted_days,
                        expires_date
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, granted_date, granted_days, expires_date)
                )

                grant_id = cur.fetchone()[0]

        return jsonify({
            "message": "有給休暇を登録しました。",
            "id": grant_id
        }), 201

    except Exception:
        current_app.logger.exception("有給休暇の付与登録に失敗しました。")

        return jsonify({
            "error": "有給休暇を登録できませんでした。"
        }), 500

@leave_bp.route("/api/leave/grants", methods=["GET"])
def get_leave_grants():
    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "error": "ログインが必要です。"
        }), 401

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        g.id,
                        g.granted_date,
                        g.granted_days,
                        g.expires_date,
                        COALESCE(SUM(u.used_days), 0) AS used_days
                    FROM leave_grants AS g
                    LEFT JOIN leave_usage AS u
                        ON g.id = u.grant_id
                        AND g.user_id = u.user_id
                    WHERE g.user_id = %s
                    GROUP BY
                        g.id,
                        g.granted_date,
                        g.granted_days,
                        g.expires_date
                    ORDER BY g.expires_date ASC, g.id ASC
                    """,
                    (user_id,)
                )

                rows = cur.fetchall()

        grants = []

        for row in rows:
            granted_days = row[2]
            used_days = row[4]
            remaining_days = granted_days - used_days

            grants.append({
                "id": row[0],
                "granted_date": row[1].isoformat(),
                "granted_days": float(granted_days),
                "expires_date": row[3].isoformat(),
                "used_days": float(used_days),
                "remaining_days": float(remaining_days)
            })
        
        return jsonify({
            "grants": grants
        }), 200

    except Exception:
        current_app.logger.exception("有給休暇の付与一覧取得に失敗しました。")

        return jsonify({
            "error": "有給休暇の付与一覧取得できませんでした。"
        }), 500

@leave_bp.route("/api/leave/usage", methods=["POST"])
def create_leave_usage():
    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "error": "ログインが必要です。"
        }), 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "入力データが正しくありません。"
        }), 400

    try:
        leave_date = date.fromisoformat(data["leave_date"])
        leave_type = data["leave_type"]
        memo = data.get("memo", "")

    except (KeyError, TypeError, ValueError):
        return jsonify({
            "error": "入力内容を確認してください。"
        }), 400

    if leave_type not in ("FULL", "AM", "PM"):
        return jsonify({
            "error": "休暇区分が正しくありません。"
        }), 400

    if not isinstance(memo, str):
        return jsonify({{
            "error": "備考が正しくありません。"
        }}), 400

    used_days = Decimal("1.0") if leave_type == "FULL" else Decimal("0.5")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (user_id,)
                )

                cur.execute(
                    """
                    SELECT id
                    FROM leave_usage
                    WHERE user_id = %s
                      AND leave_date = %s
                    LIMIT 1
                    """,
                    (user_id, leave_date)
                )

                if cur.fetchone() is not None:
                    return jsonify({
                        "error": "指定された日付には既に有給休暇が登録されています。"
                    }), 400

                cur.execute(
                    """
                    SELECT
                        g.id,
                        g.granted_days -
                            COALESCE(SUM(u.used_days), 0) AS remaining_days
                    FROM leave_grants AS g
                    LEFT JOIN leave_usage AS u
                        ON g.id = u.grant_id
                        AND g.user_id = u.user_id
                    WHERE g.user_id = %s
                      AND g.granted_date <= %s
                      AND g.expires_date >= %s
                    GROUP BY g.id, g.granted_days, g.expires_date
                    ORDER BY g.expires_date ASC, g.id ASC
                    """,
                    (user_id, leave_date, leave_date)
                )

                grants = cur.fetchall()

                grant_id = None

                for grant in grants:
                    if grant[1] >= used_days:
                        grant_id = grant[0]
                        break

                if grant_id is None:
                    return jsonify({
                        "error": "利用可能な有給休暇の残日数が不足しています。"
                    }), 400

                cur.execute(
                    """
                    INSERT INTO leave_usage (
                        user_id,
                        grant_id,
                        leave_date,
                        used_days,
                        leave_type,
                        memo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        grant_id,
                        leave_date,
                        used_days,
                        leave_type,
                        memo
                    )
                )

                usage_id = cur.fetchone()[0]

        return jsonify({
            "message": "有給休暇の使用履歴を登録しました。",
            "id": usage_id,
            "grant_id": grant_id
        }), 201

    except Exception:
        current_app.logger.exception("有給休暇の使用登録に失敗しました。")

        return jsonify({
            "error": "有給休暇の使用履歴を登録できませんでした。"
        }), 500

    