import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

from src.db.user_dao import create_user, get_user

load_dotenv()

# ==========================================
# JWT 및 토큰 설정
# ==========================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY가 .env에 설정되어 있지 않습니다."
    )

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)


# ==========================================
# 비밀번호 및 토큰 해시 함수
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False

    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")

    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"[AUTH ERROR] 비밀번호 검증 실패: {e}")
        return False


def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def hash_token(token: str) -> str:
    return bcrypt.hashpw(
        token.encode("utf-8")[:72],
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_token_hash(token: str, token_hash: str) -> bool:
    return bcrypt.checkpw(
        token.encode("utf-8")[:72],
        token_hash.encode("utf-8")
    )


# ==========================================
# 회원가입
# ==========================================

def signup(username, password):
    if not username or not password:
        return False

    password_hash = hash_password(password)

    return create_user(
        username,
        password_hash
    )


# ==========================================
# Access Token & Refresh Token 생성
# ==========================================

def create_access_token(user_id, username):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


def create_refresh_token():
    return secrets.token_urlsafe(48)


# ==========================================
# 로그인 (DictCursor 및 Tuple 모두 지원)
# ==========================================

def login(username, password):
    user = get_user(username)

    if not user:
        return None

    # DictCursor 사용 시 딕셔너리로 반환됨, 일반 커서일 경우 튜플 구조
    if isinstance(user, dict):
        user_id = user.get("id")
        db_username = user.get("username")
        password_hash = user.get("password_hash")
    else:
        user_id = user[0]
        db_username = user[1]
        password_hash = user[2]

    # 비밀번호 검증
    if not verify_password(password, password_hash):
        return None

    # Access Token 발급
    access_token = create_access_token(user_id, db_username)

    # Refresh Token 발급 및 DB 저장
    refresh_token = create_refresh_token()
    refresh_token_hashed = hash_token(refresh_token)

    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    from src.db.user_dao import save_refresh_token
    save_refresh_token(user_id, refresh_token_hashed, expires_at)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user_id,
        "username": db_username
    }


# ==========================================
# Refresh Token으로 Access Token 재발급
# ==========================================

def refresh_access_token(user_id, raw_refresh_token):
    from src.db.user_dao import get_refresh_token_info, get_user_by_id

    token_info = get_refresh_token_info(user_id)
    if not token_info:
        return None

    db_hashed_token, expires_at = token_info

    # 만료 시간 검증 (timezone 처리 체크)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        return None

    # 토큰 검증
    if not verify_token_hash(raw_refresh_token, db_hashed_token):
        return None

    user = get_user_by_id(user_id)
    if not user:
        return None

    db_username = user.get("username") if isinstance(user, dict) else user[1]
    new_access_token = create_access_token(user_id, db_username)

    return {
        "access_token": new_access_token
    }


# ==========================================
# 로그아웃
# ==========================================

def logout(user_id):
    from src.db.user_dao import delete_refresh_token
    return delete_refresh_token(user_id)


# ==========================================
# Access Token 검증
# ==========================================

def verify_token(token):
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        if payload.get("type") != "access":
            return None

        return payload

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None