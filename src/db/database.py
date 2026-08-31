import os
import pymysql
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()


class DatabaseManager:
    """MariaDB Connection Pool 관리 클래스 (Singleton)"""

    _pool = None

    @classmethod
    def get_pool(cls) -> PooledDB:
        if cls._pool is None:
            cls._pool = PooledDB(
                creator=pymysql,
                maxconnections=10,
                mincached=2,
                maxcached=5,
                blocking=True,
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
        return cls._pool

    @classmethod
    def get_connection(cls):
        return cls.get_pool().connection()


# =========================================================
# 모듈 수준의 get_connection 함수 (DAO 임포트용)
# =========================================================
def get_connection():
    """DAO 레이어에서 `from src.db.database import get_connection`으로 사용하는 헬퍼 함수"""
    return DatabaseManager.get_connection()


# =========================================================
# DB 초기화 및 테이블 자동 생성
# =========================================================
def init_db():
    """테이블 자동 생성 (MariaDB SQL 문법 및 스키마 정합성 적용)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 사용자 테이블
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            )

            # 2. 포트폴리오 테이블 (user_id에 UNIQUE 제약조건 추가 -> Upsert 동작 용도)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    age INT DEFAULT 0,
                    cash BIGINT DEFAULT 0,
                    etf_amount BIGINT DEFAULT 0,
                    bond_amount BIGINT DEFAULT 0,
                    pension_amount BIGINT DEFAULT 0,
                    monthly_etf BIGINT DEFAULT 0,
                    monthly_bond BIGINT DEFAULT 0,
                    monthly_pension BIGINT DEFAULT 0,
                    selected_etf VARCHAR(255),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            )

            # 3. 납입 계획 테이블 (user_id에 UNIQUE 제약조건 추가)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS contribution_plans (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    target_amount DECIMAL(15, 2) NOT NULL,
                    monthly_amount DECIMAL(15, 2) NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            )
            print("[DB INIT] MariaDB 테이블 및 스키마 설정 완료")
    except Exception as e:
        print(f"[DB INIT ERROR] {e}")
    finally:
        conn.close()