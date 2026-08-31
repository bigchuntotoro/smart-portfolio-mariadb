from src.db.database import get_connection


# =========================================================
# 회원가입 (신규 회원 생성)
# =========================================================
def create_user(username, password_hash, email=None):
    """
    신규 회원을 등록한다.
    email은 선택 항목이며 미전달 시 None(DB에는 NULL)으로 입력됩니다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO users (username, password_hash, email)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (username, password_hash, email))
            return cursor.lastrowid

    except Exception as e:
        print(f"[USER CREATE ERROR] {e}")
        return None

    finally:
        conn.close()


# =========================================================
# 회원 조회 (get_user 별칭 제공)
# =========================================================
def get_user_by_username(username):
    """
    사용자명(username)으로 회원 정보를 조회한다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username = %s LIMIT 1"
            cursor.execute(sql, (username,))
            return cursor.fetchone()  # DictCursor로 딕셔너리 리턴

    except Exception as e:
        print(f"[USER LOAD BY USERNAME ERROR] {e}")
        return None

    finally:
        conn.close()


def get_user(username):
    """
    auth.py 등 기존 코드와의 호환성을 위한 get_user 함수
    """
    return get_user_by_username(username)


def get_user_by_id(user_id):
    """
    회원 PK ID(user_id)로 회원 정보를 조회한다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE id = %s LIMIT 1"
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()

    except Exception as e:
        print(f"[USER LOAD BY ID ERROR] {e}")
        return None

    finally:
        conn.close()