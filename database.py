import sqlite3
import secrets
from datetime import datetime, timedelta
from typing import Optional
from config import DATABASE_PATH, SESSION_EXPIRE_DAYS


def get_connection():
    """取得資料庫連線"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫，建立表格"""
    conn = get_connection()
    cursor = conn.cursor()

    # 交易記錄表
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

    # 用戶 Session 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            display_name TEXT,
            picture_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL
        )
    """)

    # 建立索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_user_id
        ON transactions(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_created_at
        ON transactions(created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_session_id
        ON user_sessions(session_id)
    """)

    conn.commit()
    conn.close()


# ============ Session 相關函式 ============

def create_session(user_id: str, display_name: str, picture_url: Optional[str] = None) -> str:
    """建立新的 session"""
    conn = get_connection()
    cursor = conn.cursor()

    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=SESSION_EXPIRE_DAYS)

    cursor.execute("""
        INSERT INTO user_sessions (session_id, user_id, display_name, picture_url, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, user_id, display_name, picture_url, expires_at))

    conn.commit()
    conn.close()

    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """取得 session 資料"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM user_sessions
        WHERE session_id = ? AND expires_at > datetime('now')
    """, (session_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def delete_session(session_id: str) -> bool:
    """刪除 session"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_sessions WHERE session_id = ?
    """, (session_id,))

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


def cleanup_expired_sessions():
    """清理過期的 sessions"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_sessions WHERE expires_at <= datetime('now')
    """)

    conn.commit()
    conn.close()


# ============ Transaction 相關函式 ============

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


def get_transactions_paginated(
    user_id: str,
    page: int = 1,
    per_page: int = 20,
    trans_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict:
    """取得分頁的交易記錄"""
    conn = get_connection()
    cursor = conn.cursor()

    # 建構查詢條件
    conditions = ["user_id = ?"]
    params = [user_id]

    if trans_type:
        conditions.append("type = ?")
        params.append(trans_type)

    if category:
        conditions.append("category = ?")
        params.append(category)

    if start_date:
        conditions.append("date(created_at) >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("date(created_at) <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    # 計算總數
    cursor.execute(f"""
        SELECT COUNT(*) as total FROM transactions WHERE {where_clause}
    """, params)
    total = cursor.fetchone()["total"]

    # 取得分頁資料
    offset = (page - 1) * per_page
    cursor.execute(f"""
        SELECT * FROM transactions
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    rows = cursor.fetchall()
    conn.close()

    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


def get_transaction_by_id(transaction_id: int, user_id: str) -> Optional[dict]:
    """取得單筆交易記錄"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM transactions
        WHERE id = ? AND user_id = ?
    """, (transaction_id, user_id))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def update_transaction(
    transaction_id: int,
    user_id: str,
    trans_type: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None
) -> bool:
    """更新交易記錄"""
    conn = get_connection()
    cursor = conn.cursor()

    # 先確認記錄存在且屬於該用戶
    cursor.execute("""
        SELECT id FROM transactions WHERE id = ? AND user_id = ?
    """, (transaction_id, user_id))

    if not cursor.fetchone():
        conn.close()
        return False

    # 建構更新語句
    updates = []
    params = []

    if trans_type is not None:
        updates.append("type = ?")
        params.append(trans_type)

    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)

    if category is not None:
        updates.append("category = ?")
        params.append(category)

    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if not updates:
        conn.close()
        return True

    params.extend([transaction_id, user_id])
    cursor.execute(f"""
        UPDATE transactions
        SET {", ".join(updates)}
        WHERE id = ? AND user_id = ?
    """, params)

    conn.commit()
    conn.close()
    return True


def delete_transaction(transaction_id: int, user_id: str) -> bool:
    """刪除交易記錄"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM transactions WHERE id = ? AND user_id = ?
    """, (transaction_id, user_id))

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


# ============ 統計相關函式 ============

def get_summary(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> dict:
    """取得收入支出總計"""
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["user_id = ?"]
    params = [user_id]

    if start_date:
        conditions.append("date(created_at) >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("date(created_at) <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    cursor.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE {where_clause}
    """, params)

    row = cursor.fetchone()
    conn.close()

    return {
        "total_income": row["total_income"],
        "total_expense": row["total_expense"],
        "balance": row["total_income"] - row["total_expense"],
        "transaction_count": row["transaction_count"]
    }


def get_stats_by_category(
    user_id: str,
    trans_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> list:
    """取得分類統計"""
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["user_id = ?"]
    params = [user_id]

    if trans_type:
        conditions.append("type = ?")
        params.append(trans_type)

    if start_date:
        conditions.append("date(created_at) >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("date(created_at) <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    cursor.execute(f"""
        SELECT
            category,
            type,
            SUM(amount) as total,
            COUNT(*) as count
        FROM transactions
        WHERE {where_clause}
        GROUP BY category, type
        ORDER BY total DESC
    """, params)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_stats_by_date(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day"  # day, week, month
) -> list:
    """取得日期趨勢統計"""
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["user_id = ?"]
    params = [user_id]

    if start_date:
        conditions.append("date(created_at) >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("date(created_at) <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    # 根據 group_by 設定日期格式
    if group_by == "month":
        date_format = "%Y-%m"
    elif group_by == "week":
        date_format = "%Y-%W"
    else:  # day
        date_format = "%Y-%m-%d"

    cursor.execute(f"""
        SELECT
            strftime('{date_format}', created_at) as date,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        WHERE {where_clause}
        GROUP BY strftime('{date_format}', created_at)
        ORDER BY date ASC
    """, params)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_categories(user_id: str) -> list:
    """取得用戶使用過的所有分類"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT category FROM transactions
        WHERE user_id = ?
        ORDER BY category
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [row["category"] for row in rows]


def get_all_transactions_for_export(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> list:
    """取得所有交易記錄（用於匯出）"""
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["user_id = ?"]
    params = [user_id]

    if start_date:
        conditions.append("date(created_at) >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("date(created_at) <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    cursor.execute(f"""
        SELECT * FROM transactions
        WHERE {where_clause}
        ORDER BY created_at DESC
    """, params)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# 初始化資料庫
init_db()
