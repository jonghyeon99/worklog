from datetime import date, time, datetime
from flask import Blueprint, jsonify, request, session, current_app
from psycopg.errors import UniqueViolation
from db import get_connection
import calendar

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

    today = date.today()

    try:
        year = int(request.args.get("year", today.year))
        month = int(request.args.get("month", today.month))

        if year < 1 or year > 9999 or month < 1 or month > 12:
            return jsonify({
                "error": "年月が正しくありません。"
            }), 400

        last_day = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)

    except ValueError:
        return jsonify({
            "error": "年月が正しくありません。"
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_date, clock_in, clock_out,
                           break_start, break_end, memo
                    FROM work_record
                    WHERE user_id = %s
                      AND work_date BETWEEN %s AND %s
                    ORDER BY work_date DESC
                    """,
                    (user_id, start_date, end_date)
                )
                rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT default_clock_in, default_clock_out,
                           default_break_start, default_break_end
                    FROM work_setting
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                setting = cur.fetchone()

                if setting is None:
                    return jsonify({
                        "error": "勤務時間の設定が見つかりません。"
                    }), 404

                cur.execute(
                    """
                    SELECT leave_date, leave_type
                    FROM paid_leave_usage
                    WHERE user_id = %s
                      AND leave_date BETWEEN %s AND %s
                    """,
                    (user_id, start_date, end_date)
                )
                leave_rows = cur.fetchall()

        standard_minutes = calculate_work_minutes(
            setting[0], setting[1], setting[2], setting[3]
        )

        leave_map = {}

        for leave_date, leave_type in leave_rows:
            if leave_date in leave_map:
                return jsonify({
                    "error": "同じ日付に複数の休暇記録があります。"
                }), 409

            leave_map[leave_date] = leave_type

        attendance_list = []
        total_work_minutes = 0
        total_overtime_minutes = 0

        for row in rows:
            work_date = row[1]
            work_minutes = calculate_work_minutes(
                row[2], row[3], row[4], row[5]
            )

            leave_type = leave_map.get(work_date)

            if leave_type == "FULL":
                return jsonify({
                    "error": "全日休暇と勤怠記録が重複しています。"
                }), 409

            if leave_type in ("AM", "PM"):
                required_minutes = standard_minutes // 2
            else:
                required_minutes = standard_minutes

            overtime_minutes = max(
                0, work_minutes - required_minutes
            )

            total_work_minutes += work_minutes
            total_overtime_minutes += overtime_minutes

            attendance_list.append({
                "id": row[0],
                "work_date": work_date.isoformat(),
                "clock_in": row[2].strftime("%H:%M"),
                "clock_out": row[3].strftime("%H:%M"),
                "break_start": row[4].strftime("%H:%M") if row[4] else None,
                "break_end": row[5].strftime("%H:%M") if row[5] else None,
                "memo": row[6] or "",
                "work_minutes": work_minutes,
                "work_time": format_work_minutes(work_minutes),
                "overtime_minutes": overtime_minutes,
                "overtime_time": format_work_minutes(overtime_minutes)
            })

        return jsonify({
            "year": year,
            "month": month,
            "attendance": attendance_list,
            "work_days": len(attendance_list),
            "total_work_minutes": total_work_minutes,
            "total_work_time": format_work_minutes(total_work_minutes),
            "total_overtime_minutes": total_overtime_minutes,
            "total_overtime": format_work_minutes(total_overtime_minutes)
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
                    INSERT INTO work_record (
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
                    UPDATE work_record
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
                    DELETE FROM work_record
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
                    FROM work_setting
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

def calculate_work_minutes(clock_in, clock_out, break_start, break_end):
    start = datetime.combine(date.today(), clock_in)
    end = datetime.combine(date.today(), clock_out)

    work_minutes = int((end - start).total_seconds() // 60)

    if break_start is not None and break_end is not None:
        break_start_dt = datetime.combine(date.today(), break_start)
        break_end_dt = datetime.combine(date.today(), break_end)

        break_minutes = int((break_end_dt - break_start_dt).total_seconds() // 60)

        work_minutes -= break_minutes
    
    return work_minutes

def format_work_minutes(minutes):
    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}時間{remaining_minutes:02d}分"















