import os
import pymysql
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            cls._pool = PooledDB(
                creator=pymysql,
                maxconnections=10,
                mincached=2,
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        return cls._pool

    @classmethod
    def get_connection(cls):
        return cls.get_pool().connection()

def init_db():
    """테이블 자동 생성 (MariaDB SQL 문법 적용)"""
    conn = DatabaseManager.get_connection()
    with conn.cursor() as cursor:
        # 1. 사용자 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 2. 포트폴리오 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                portfolio_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 3. 납입 계획 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contribution_plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                target_amount DECIMAL(15, 2) NOT NULL,
                monthly_amount DECIMAL(15, 2) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
    conn.close()