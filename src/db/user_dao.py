from src.db.database import get_connection


# =========================================================
# 회원 등록 / 조회
# =========================================================

def create_user(username, password_hash, email=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                  INSERT INTO users (username, password_hash, email)
                  VALUES (%s, %s, %s) \
                  """
            cursor.execute(sql, (username, password_hash, email))
            return cursor.lastrowid
    except Exception as e:
        print(f"[USER CREATE ERROR] {e}")
        return None
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, username, password_hash, email FROM users WHERE username = %s LIMIT 1"
            cursor.execute(sql, (username,))
            return cursor.fetchone()  # DictCursor 적용: {'id': ..., 'username': ..., ...}
    except Exception as e:
        print(f"[USER LOAD BY USERNAME ERROR] {e}")
        return None
    finally:
        conn.close()


def get_user(username):
    return get_user_by_username(username)


def get_user_by_id(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, username, password_hash, email FROM users WHERE id = %s LIMIT 1"
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"[USER LOAD BY ID ERROR] {e}")
        return None
    finally:
        conn.close()


# =========================================================
# Refresh Token 관련 DB CRUD (MariaDB / Upsert)
# =========================================================

def save_refresh_token(user_id, refresh_token_hash, expires_at):
    """
    Refresh Token 정보를 저장합니다 (이미 존재하면 UPDATE).
    refresh_tokens 테이블이 없으면 자동 생성합니다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # refresh_tokens 테이블 생성 보장
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS refresh_tokens
                           (
                               user_id
                               INT
                               PRIMARY
                               KEY,
                               refresh_token_hash
                               VARCHAR
                           (
                               255
                           ) NOT NULL,
                               expires_at DATETIME NOT NULL,
                               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                               FOREIGN KEY
                           (
                               user_id
                           ) REFERENCES users
                           (
                               id
                           )
                                                                              ON DELETE CASCADE
                               ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                           """)

            sql = """
                  INSERT INTO refresh_tokens (user_id, refresh_token_hash, expires_at)
                  VALUES (%s, %s, %s) ON DUPLICATE KEY \
                  UPDATE \
                      refresh_token_hash = \
                  VALUES (refresh_token_hash), expires_at = \
                  VALUES (expires_at), updated_at = CURRENT_TIMESTAMP \
                  """
            cursor.execute(sql, (user_id, refresh_token_hash, expires_at))
            return True
    except Exception as e:
        print(f"[SAVE REFRESH TOKEN ERROR] {e}")
        return False
    finally:
        conn.close()


def get_refresh_token_info(user_id):
    """
    저장된 Refresh Token 정보 (hash, expires_at)를 조회합니다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT refresh_token_hash, expires_at FROM refresh_tokens WHERE user_id = %s LIMIT 1"
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None

            if isinstance(row, dict):
                return row.get("refresh_token_hash"), row.get("expires_at")
            return row[0], row[1]
    except Exception as e:
        print(f"[GET REFRESH TOKEN ERROR] {e}")
        return None
    finally:
        conn.close()


def delete_refresh_token(user_id):
    """
    로그아웃 시 Refresh Token을 DB에서 삭제합니다.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM refresh_tokens WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            return True
    except Exception as e:
        print(f"[DELETE REFRESH TOKEN ERROR] {e}")
        return False
    finally:
        conn.close()