import sqlite3
from datetime import datetime
from typing import Optional
from config import DATABASE_PATH


def get_connection():
    """取得資料庫連線"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫，建立表格"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def add_transaction(
    user_id: str,
    trans_type: str,
    amount: float,
    category: str,
    description: Optional[str] = None
) -> int:
    """新增一筆交易記錄"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions (user_id, type, amount, category, description)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, trans_type, amount, category, description))

    transaction_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return transaction_id


def get_transactions(user_id: str, limit: int = 10) -> list:
    """取得用戶的交易記錄"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# 初始化資料庫
init_db()
