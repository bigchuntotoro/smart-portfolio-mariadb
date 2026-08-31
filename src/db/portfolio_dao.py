from src.db.database import DatabaseManager


# =========================================================
# 회원별 포트폴리오 조회
# =========================================================

def get_portfolio(user_id):
    """
    로그인한 회원의 포트폴리오를 조회한다.

    Parameters
    ----------
    user_id : int
        로그인한 회원 ID

    Returns
    -------
    dict | None
    """

    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    conn = DatabaseManager.get_connection()

    try:
        with conn.cursor() as cursor:
            # MariaDB 파라미터 바인딩: ? -> %s
            cursor.execute(
                """
                SELECT
                    age,
                    cash,
                    etf_amount,
                    bond_amount,
                    pension_amount,
                    monthly_etf,
                    monthly_bond,
                    monthly_pension,
                    selected_etf
                FROM portfolios
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            # DictCursor 및 일반 Cursor(튜플) 모두 호환 처리
            if isinstance(row, dict):
                return {
                    "age": int(row.get("age") or 0),
                    "cash": int(row.get("cash") or 0),
                    "etf_amount": int(row.get("etf_amount") or 0),
                    "bond_amount": int(row.get("bond_amount") or 0),
                    "pension_amount": int(row.get("pension_amount") or 0),
                    "monthly_etf": int(row.get("monthly_etf") or 0),
                    "monthly_bond": int(row.get("monthly_bond") or 0),
                    "monthly_pension": int(row.get("monthly_pension") or 0),
                    "selected_etf": row.get("selected_etf") or "",
                }
            else:
                return {
                    "age": int(row[0] or 0),
                    "cash": int(row[1] or 0),
                    "etf_amount": int(row[2] or 0),
                    "bond_amount": int(row[3] or 0),
                    "pension_amount": int(row[4] or 0),
                    "monthly_etf": int(row[5] or 0),
                    "monthly_bond": int(row[6] or 0),
                    "monthly_pension": int(row[7] or 0),
                    "selected_etf": row[8] or "",
                }

    except Exception as e:
        print(f"[PORTFOLIO LOAD ERROR] {e}")
        return None

    finally:
        conn.close()


# =========================================================
# 회원별 포트폴리오 저장
# =========================================================

def save_portfolio(
    user_id,
    age,
    cash,
    etf_amount,
    bond_amount,
    pension_amount,
    monthly_etf,
    monthly_bond,
    monthly_pension,
    selected_etf,
):
    """
    회원별 포트폴리오를 저장한다.

    이미 존재하는 user_id라면 UPDATE,
    없으면 INSERT 한다. (ON DUPLICATE KEY UPDATE 구문 적용)
    """

    if user_id is None:
        return False

    try:
        user_id = int(user_id)
        age = int(age)
        cash = int(cash)
        etf_amount = int(etf_amount)
        bond_amount = int(bond_amount)
        pension_amount = int(pension_amount)
        monthly_etf = int(monthly_etf)
        monthly_bond = int(monthly_bond)
        monthly_pension = int(monthly_pension)
    except (TypeError, ValueError):
        return False

    conn = DatabaseManager.get_connection()

    try:
        with conn.cursor() as cursor:
            # =================================================
            # 1. users 테이블에 회원 존재 여부 확인
            # =================================================
            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )

            user = cursor.fetchone()

            if user is None:
                print(
                    f"[PORTFOLIO SAVE ERROR] "
                    f"존재하지 않는 user_id={user_id}"
                )
                return False

            # =================================================
            # 2. 포트폴리오 저장 (MariaDB Upsert 적용)
            # =================================================
            cursor.execute(
                """
                INSERT INTO portfolios (
                    user_id,
                    age,
                    cash,
                    etf_amount,
                    bond_amount,
                    pension_amount,
                    monthly_etf,
                    monthly_bond,
                    monthly_pension,
                    selected_etf
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    age = VALUES(age),
                    cash = VALUES(cash),
                    etf_amount = VALUES(etf_amount),
                    bond_amount = VALUES(bond_amount),
                    pension_amount = VALUES(pension_amount),
                    monthly_etf = VALUES(monthly_etf),
                    monthly_bond = VALUES(monthly_bond),
                    monthly_pension = VALUES(monthly_pension),
                    selected_etf = VALUES(selected_etf),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    age,
                    cash,
                    etf_amount,
                    bond_amount,
                    pension_amount,
                    monthly_etf,
                    monthly_bond,
                    monthly_pension,
                    selected_etf,
                ),
            )

        print(
            f"[PORTFOLIO SAVE] "
            f"user_id={user_id}, "
            f"selected_etf={selected_etf}"
        )

        return True

    except Exception as e:
        print(f"[PORTFOLIO SAVE ERROR] {e}")
        return False

    finally:
        conn.close()


# =========================================================
# 회원별 포트폴리오 삭제
# =========================================================

def delete_portfolio(user_id):
    """
    회원의 포트폴리오를 삭제한다.
    """

    if user_id is None:
        return False

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return False

    conn = DatabaseManager.get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM portfolios
                WHERE user_id = %s
                """,
                (user_id,),
            )

        return True

    except Exception as e:
        print(f"[PORTFOLIO DELETE ERROR] {e}")
        return False

    finally:
        conn.close()