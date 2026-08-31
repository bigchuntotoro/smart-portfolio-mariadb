from src.db.database import DatabaseManager

def create_user(username, password_hash, email):
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            # SQLite의 '?' 대신 '%s' 사용
            sql = "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)"
            cursor.execute(sql, (username, password_hash, email))
            return cursor.lastrowid
    finally:
        conn.close()

def get_user_by_username(username):
    conn = DatabaseManager.get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            return cursor.fetchone()  # DictCursor 덕분에 딕셔너리로 리턴됨
    finally:
        conn.close()