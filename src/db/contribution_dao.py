import json
from typing import Any, Dict

from src.db.database import get_connection

# 관리 대상 연도
YEARS = [2026, 2027, 2028, 2029, 2030]

# 연도별 기본 시작/종료월 (2026년만 9~12월, 나머지는 1~12월 전체)
DEFAULT_START_END = {
    2026: (9, 12),
}

# 기본 세팅값 (ETF별 1~12월 0원 배열)
DEFAULT_MONTHLY_DATA = {
    "p_sp500": [0] * 12,
    "p_nasdaq": [0] * 12,
    "p_dividend": [0] * 12,
    "i_high_div": [0] * 12,
    "i_cover_call": [0] * 12,
    "i_bond": [0] * 12,
    "isa_sp500": [0] * 12,
    "isa_nasdaq": [0] * 12,
    "isa_semicon": [0] * 12,
}


def _default_monthly_data() -> Dict[str, Any]:
    return {k: v.copy() for k, v in DEFAULT_MONTHLY_DATA.items()}


def _default_yearly_plan() -> Dict[str, Any]:
    """연도별 기본 플랜 전체를 생성합니다."""
    plan = {}
    for year in YEARS:
        start, end = DEFAULT_START_END.get(year, (1, 12))
        plan[str(year)] = {
            "start_month": start,
            "end_month": end,
            "monthly_data": _default_monthly_data(),
        }
    return plan


def get_user_plan(user_id: int) -> Dict[str, Any]:
    """사용자의 연도별 연금 및 ISA 납입 플랜을 DB에서 조회합니다."""
    query = """
        SELECT year, monthly_data, start_month, end_month
        FROM contribution_plans
        WHERE user_id = %s
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id,))
            rows = cursor.fetchall()

        plan = _default_yearly_plan()

        for row in rows:
            # DictCursor 및 일반 Tuple 커서 모두 대응
            if isinstance(row, dict):
                year_val = row.get("year")
                raw_json = row.get("monthly_data")
                start_m = row.get("start_month", 1)
                end_m = row.get("end_month", 12)
            else:
                year_val, raw_json, start_m, end_m = row[0], row[1], row[2], row[3]

            year_key = str(year_val)
            if year_key not in plan:
                plan[year_key] = {"start_month": 1, "end_month": 12, "monthly_data": _default_monthly_data()}

            try:
                monthly_data = json.loads(raw_json) if raw_json else _default_monthly_data()
            except (TypeError, json.JSONDecodeError):
                monthly_data = _default_monthly_data()

            merged_monthly_data = _default_monthly_data()
            if isinstance(monthly_data, dict):
                merged_monthly_data.update(monthly_data)

            plan[year_key] = {
                "start_month": start_m,
                "end_month": end_m,
                "monthly_data": merged_monthly_data,
            }

        return plan
    except Exception as e:
        print(f"[DB ERROR] get_user_plan 실패 (user_id: {user_id}): {e}")
        return _default_yearly_plan()
    finally:
        if conn:
            conn.close()


def save_user_plan(user_id: int, plan_data: Dict[str, Any]) -> bool:
    """사용자의 연도별 연금 및 ISA 납입 플랜을 MariaDB에 저장/업데이트합니다."""
    if "monthly_data" in plan_data and "start_month" in plan_data:
        plan_data = {"2026": plan_data}

    # MariaDB Upsert 문법 적용 (%s 바인딩 + ON DUPLICATE KEY UPDATE)
    query = """
        INSERT INTO contribution_plans (
            user_id, year, monthly_data, start_month, end_month, updated_at
        ) VALUES (%s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            monthly_data = VALUES(monthly_data),
            start_month = VALUES(start_month),
            end_month = VALUES(end_month),
            updated_at = NOW();
    """

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            for year_key, year_plan in plan_data.items():
                monthly_data = year_plan.get("monthly_data", DEFAULT_MONTHLY_DATA)

                clean_monthly_data = {}
                for key, values in monthly_data.items():
                    clean_monthly_data[key] = [int(v) if v is not None else 0 for v in values]

                monthly_json_str = json.dumps(clean_monthly_data, ensure_ascii=False)

                params = (
                    user_id,
                    int(year_key),
                    monthly_json_str,
                    year_plan.get("start_month", 1),
                    year_plan.get("end_month", 12),
                )
                cursor.execute(query, params)

        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB ERROR] save_user_plan 실패 (user_id: {user_id}): {e}")
        return False
    finally:
        if conn:
            conn.close()