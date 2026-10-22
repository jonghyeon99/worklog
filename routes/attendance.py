from datetime import date, time
from flask import Blueprint, jsonify, request, session, current_app
from psycopg.errors import UniqueViolation
from db import get_connection

attendance_bp = Blueprint("attendance", __name__)

def validate_attendance(data):
    if not isinstance(data, dict):
        return None, "リクエスト形式が正しくありません。"

    work_date = data.get("work_date")
    clock_in = data.get("clock_in")
    clock_out = data.get("clock_out")
    break_start = data.get("break_start")
    break_end = data.get("break_end")
    memo = data.get("memo", "")

    try:
        work_date = date.fromisoformat(work_date)
        clock_in = time.fromisoformat(clock_in)
        clock_out = time.fromisoformat(clock_out)

        if break_start == "":
            break_start = None

        if break_end == "":
            break_end = None

        if break_start is not None:
            break_start = time.fromisoformat(break_start)

        if break_end is not None:
            break_end = time.fromisoformat(break_end)

    except (TypeError, ValueError):
        return None, "日付または時刻の形式が正しくありません。"

    if clock_in >= clock_out:
        return None, "退勤時刻は出勤時刻より後にしてください。"

    if (break_start is None) != (break_end is None):
        return None, "休憩開始と終了は両方入力してください。"
    
    if break_start is not None:
        if break_start >= break_end:
            return None, "休憩終了時刻は休憩開始時刻より後にしてください。"

        if break_start < clock_in or break_end > clock_out:
            return None, "休憩時間は勤務時間内に設定してください。"

    if not isinstance(memo, str):
        return None, "メモの形式が正しくありません。"

    if len(memo) > 1000:
        return None, "メモは1000文字以内で入力してください。"

    return {
        "work_date": work_date,
        "clock_in": clock_in,
        "clock_out": clock_out,
        "break_start": break_start,
        "break_end": break_end,
        "memo": memo
    }, None

def format_attendance(row):
    return {
        "id": row[0],
        "work_date": row[1].isoformat(),
        "clock_in": row[2].strftime("%H:%M"),
        "clock_out": row[3].strftime("%H:%M"),
        "break_start": row[4].strftime("%H:%M") if row[4] else None,
        "break_end": row[5].strftime("%H:%M") if row[5] else None,
        "memo": row[6]
    }

@attendance_bp.route("/api/attendance", methods=["GET"])
def attendance_list():
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
                    SELECT id, work_date, clock_in, clock_out,
                           break_start, break_end, memo
                    FROM attendance
                    WHERE user_id = %s
                    ORDER BY work_date DESC
                    """,
                    (user_id,)
                )
                rows = cur.fetchall()

        return jsonify({
            "attendance": [format_attendance(row) for row in rows]
        }), 200

    except Exception:
        current_app.logger.exception("勤怠一覧の取得に失敗しました。")
        return jsonify({
            "error": "勤怠一覧を取得できませんでした。"
        }), 500

@attendance_bp.route("/api/attendance", methods=["POST"])
def attendance_create():
    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "error": "ログインが必要です。"
        }), 401

    data, error = validate_attendance(request.get_json(silent=True))

    if error:
        return jsonify({
            "error": error
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO attendance (
                        user_id, work_date, clock_in, clock_out,
                        break_start, break_end, memo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        data["work_date"],
                        data["clock_in"],
                        data["clock_out"],
                        data["break_start"],
                        data["break_end"],
                        data["memo"]
                    )
                )
                attendance_id = cur.fetchone()[0]
        
        return jsonify({
            "message": "勤怠記録を登録しました。",
            "id": attendance_id
        }), 201
    
    except UniqueViolation:
        return jsonify({
            "error": "この日付の勤怠記録は既に登録されています。"
        }), 409

    except Exception:
        current_app.logger.exception("勤怠記録の登録に失敗しました。")
        return jsonify({
            "error": "勤怠記録を登録できませんでした。"
        }), 500

@attendance_bp.route("/api/attendance/<int:attendance_id>", methods=["PUT"])
def attendance_update(attendance_id):
    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "error": "ログインが必要です。"
        }), 401

    data, error = validate_attendance(request.get_json(silent=True))

    if error:
        return jsonify({
            "error": error
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE attendance
                    SET work_date = %s,
                        clock_in = %s,
                        clock_out = %s,
                        break_start = %s,
                        break_end = %s,
                        memo = %s,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (
                        data["work_date"],
                        data["clock_in"],
                        data["clock_out"],
                        data["break_start"],
                        data["break_end"],
                        data["memo"],
                        attendance_id,
                        user_id
                    )
                )
                row = cur.fetchone()

        if row is None:
            return jsonify({
                "error": "勤怠記録が見つかりません。"
                }), 404

        return jsonify({
            "message": "勤怠記録を更新しました。"
            }), 200

    except UniqueViolation:
        return jsonify({
            "error": "この日付の勤怠記録は既に登録されています。"
        }), 409

    except Exception:
        current_app.logger.exception("勤怠記録の更新に失敗しました。")
        return jsonify({
            "error": "勤怠記録を更新できませんでした。"
            }), 500

@attendance_bp.route("/api/attendance/<int:attendance_id>", methods=["DELETE"])
def attendance_delete(attendance_id):
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
                    DELETE FROM attendance
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (attendance_id, user_id)
                )
                row = cur.fetchone()

        if row is None:
            return jsonify({
                "error": "勤怠記録が見つかりません。"
                }), 404

        return jsonify({
            "message": "勤怠記録を削除しました。"
            }), 200

    except Exception:
        current_app.logger.exception("勤怠記録の削除に失敗しました。")
        return jsonify({
            "error": "勤怠記録を削除できませんでした。"
            }), 500

@attendance_bp.route("/api/attendance/settings", methods=["GET"])
def attendance_settings():
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
                    SELECT default_clock_in, default_clock_out,
                           default_break_start, default_break_end
                    FROM user_settings
                    WHERE user_id = %s
                    """, 
                    (user_id,)
                )
                row = cur.fetchone()

        if row is None:
            return jsonify({
                "error": "勤務時間の設定が見つかりません。"
            }), 404

        return jsonify({
            "clock_in": row[0].strftime("%H:%M"),
            "clock_out": row[1].strftime("%H:%M"),
            "break_start": row[2].strftime("%H:%M") if row[2] else "",
            "break_end": row[3].strftime("%H:%M") if row[3] else "",
        }), 200

    except Exception:
        current_app.logger.exception("勤務時間設定の取得に失敗しました。")
        return jsonify({
            "error": "勤務時間設定を取得できませんでした。"
        }), 500