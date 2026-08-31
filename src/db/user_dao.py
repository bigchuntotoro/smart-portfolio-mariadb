from src.db.database import get_connection


def create_user(username, password_hash, email=None):
    """
    신규 회원을 등록한다.
    email은 선택 항목이므로 전달되지 않을 경우 None(DB에는 NULL)으로 처리됩니다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # MariaDB 파라미터 바인딩 (%s 사용)
            sql = """
                  INSERT INTO users (username, password_hash, email)
                  VALUES (%s, %s, %s) \
                  """
            cursor.execute(sql, (username, password_hash, email))

            # 생성된 사용자 ID(AUTO_INCREMENT) 반환
            return cursor.lastrowid

    except Exception as e:
        print(f"[USER CREATE ERROR] {e}")
        return None

    finally:
        conn.close()


def get_user_by_username(username):
    """
    사용자명(username)으로 회원 정보를 조회한다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username = %s LIMIT 1"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
            return user  # DictCursor 덕분에 딕셔너리 형태로 리턴됨

    except Exception as e:
        print(f"[USER LOAD ERROR] {e}")
        return None

    finally:
        conn.close()


def get_user_by_id(user_id):
    """
    회원 ID(user_id)로 회원 정보를 조회한다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE id = %s LIMIT 1"
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()
            return user

    except Exception as e:
        print(f"[USER LOAD BY ID ERROR] {e}")
        return None

    finally:
        conn.close()