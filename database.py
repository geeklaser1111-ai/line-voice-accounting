import libsql_experimental as libsql
import secrets
from datetime import datetime, timedelta
from typing import Optional
from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, SESSION_EXPIRE_DAYS


def get_connection():
    """取得資料庫連線"""
    conn = libsql.connect(
        TURSO_DATABASE_URL,
        auth_token=TURSO_AUTH_TOKEN
    )
    return conn


def dict_row(cursor, row):
    """將 row 轉換為 dict"""
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


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

    # 預算設定表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            monthly_budget REAL NOT NULL DEFAULT 0,
            category TEXT,
            category_budget REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 固定收支表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            day_of_month INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_executed DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 習慣表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '✓',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 習慣打卡表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            habit_id INTEGER NOT NULL,
            check_date DATE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, habit_id, check_date)
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
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_budgets_user_id
        ON budgets(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_recurring_user_id
        ON recurring_transactions(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_habits_user_id
        ON habits(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_habit_checkins_user_habit
        ON habit_checkins(user_id, habit_id)
    """)

    # 固定支出提醒表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expense_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            day_of_month INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_expense_reminders_user_id
        ON expense_reminders(user_id)
    """)

    # OAuth State 暫存表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()


# ============ Session 相關函式 ============

def create_session(user_id: str, display_name: str, picture_url: Optional[str] = None) -> str:
    """建立新的 session"""
    conn = get_connection()
    cursor = conn.cursor()

    session_id = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(days=SESSION_EXPIRE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO user_sessions (session_id, user_id, display_name, picture_url, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, user_id, display_name, picture_url or "", expires_at))

    conn.commit()

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
    result = dict_row(cursor, row)

    return result


def delete_session(session_id: str) -> bool:
    """刪除 session"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_sessions WHERE session_id = ?
    """, (session_id,))

    deleted = cursor.rowcount > 0
    conn.commit()

    return deleted


def cleanup_expired_sessions():
    """清理過期的 sessions"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_sessions WHERE expires_at <= datetime('now')
    """)

    conn.commit()


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
    result = [dict_row(cursor, row) for row in rows]

    return result


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
    total_row = cursor.fetchone()
    total = dict_row(cursor, total_row)["total"]

    # 取得分頁資料
    offset = (page - 1) * per_page
    cursor.execute(f"""
        SELECT * FROM transactions
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    rows = cursor.fetchall()

    return {
        "items": [dict_row(cursor, row) for row in rows],
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

    return dict_row(cursor, row) if row else None


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
            return True

    params.extend([transaction_id, user_id])
    cursor.execute(f"""
        UPDATE transactions
        SET {", ".join(updates)}
        WHERE id = ? AND user_id = ?
    """, params)

    conn.commit()
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
    result = dict_row(cursor, row)

    return {
        "total_income": result["total_income"],
        "total_expense": result["total_expense"],
        "balance": result["total_income"] - result["total_expense"],
        "transaction_count": result["transaction_count"]
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

    return [dict_row(cursor, row) for row in rows]


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

    return [dict_row(cursor, row) for row in rows]


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

    return [dict_row(cursor, row)["category"] for row in rows]


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

    return [dict_row(cursor, row) for row in rows]


# ============ 預算相關函式 ============

def get_budget(user_id: str) -> Optional[dict]:
    """取得用戶的預算設定"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM budgets
        WHERE user_id = ? AND category IS NULL
    """, (user_id,))

    row = cursor.fetchone()

    return dict_row(cursor, row) if row else None


def set_budget(user_id: str, monthly_budget: float) -> int:
    """設定每月總預算"""
    conn = get_connection()
    cursor = conn.cursor()

    # 檢查是否已有預算設定
    cursor.execute("""
        SELECT id FROM budgets WHERE user_id = ? AND category IS NULL
    """, (user_id,))

    existing_row = cursor.fetchone()
    existing = dict_row(cursor, existing_row) if existing_row else None

    if existing:
        cursor.execute("""
            UPDATE budgets
            SET monthly_budget = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (monthly_budget, existing["id"]))
        budget_id = existing["id"]
    else:
        cursor.execute("""
            INSERT INTO budgets (user_id, monthly_budget)
            VALUES (?, ?)
        """, (user_id, monthly_budget))
        budget_id = cursor.lastrowid

    conn.commit()

    return budget_id


def get_budget_status(user_id: str) -> dict:
    """取得預算使用狀況"""
    # 取得預算設定
    budget = get_budget(user_id)
    monthly_budget = budget["monthly_budget"] if budget else 0

    # 取得本月支出
    today = datetime.now()
    start_date = today.replace(day=1).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    summary = get_summary(user_id, start_date=start_date, end_date=end_date)
    spent = summary["total_expense"]

    remaining = monthly_budget - spent
    percentage = (spent / monthly_budget * 100) if monthly_budget > 0 else 0

    return {
        "monthly_budget": monthly_budget,
        "spent": spent,
        "remaining": remaining,
        "percentage": round(percentage, 1),
        "is_over_budget": remaining < 0
    }


# ============ 固定收支相關函式 ============

def add_recurring_transaction(
    user_id: str,
    trans_type: str,
    amount: float,
    category: str,
    description: Optional[str] = None,
    day_of_month: int = 1
) -> int:
    """新增固定收支"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO recurring_transactions
        (user_id, type, amount, category, description, day_of_month)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, trans_type, amount, category, description, day_of_month))

    recurring_id = cursor.lastrowid
    conn.commit()

    return recurring_id


def get_recurring_transactions(user_id: str) -> list:
    """取得用戶的固定收支列表"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM recurring_transactions
        WHERE user_id = ? AND is_active = 1
        ORDER BY day_of_month ASC
    """, (user_id,))

    rows = cursor.fetchall()

    return [dict_row(cursor, row) for row in rows]


def get_recurring_transaction_by_id(recurring_id: int, user_id: str) -> Optional[dict]:
    """取得單筆固定收支"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM recurring_transactions
        WHERE id = ? AND user_id = ?
    """, (recurring_id, user_id))

    row = cursor.fetchone()

    return dict_row(cursor, row) if row else None


def update_recurring_transaction(
    recurring_id: int,
    user_id: str,
    trans_type: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    day_of_month: Optional[int] = None,
    is_active: Optional[int] = None
) -> bool:
    """更新固定收支"""
    conn = get_connection()
    cursor = conn.cursor()

    # 確認記錄存在
    cursor.execute("""
        SELECT id FROM recurring_transactions WHERE id = ? AND user_id = ?
    """, (recurring_id, user_id))

    if not cursor.fetchone():
            return False

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
    if day_of_month is not None:
        updates.append("day_of_month = ?")
        params.append(day_of_month)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)

    if not updates:
            return True

    params.extend([recurring_id, user_id])
    cursor.execute(f"""
        UPDATE recurring_transactions
        SET {", ".join(updates)}
        WHERE id = ? AND user_id = ?
    """, params)

    conn.commit()
    return True


def delete_recurring_transaction(recurring_id: int, user_id: str) -> bool:
    """刪除固定收支"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM recurring_transactions WHERE id = ? AND user_id = ?
    """, (recurring_id, user_id))

    deleted = cursor.rowcount > 0
    conn.commit()

    return deleted


def execute_recurring_transactions():
    """執行今天應該執行的固定收支（由排程呼叫）"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    day_of_month = today.day

    # 找出今天要執行的固定收支
    cursor.execute("""
        SELECT * FROM recurring_transactions
        WHERE is_active = 1
        AND day_of_month = ?
        AND (last_executed IS NULL OR last_executed < ?)
    """, (day_of_month, today_str))

    rows = cursor.fetchall()
    # 先轉換所有 rows 為 dict
    rows_dict = [dict_row(cursor, row) for row in rows]
    executed_count = 0

    for row in rows_dict:
        # 新增交易
        cursor.execute("""
            INSERT INTO transactions (user_id, type, amount, category, description)
            VALUES (?, ?, ?, ?, ?)
        """, (row["user_id"], row["type"], row["amount"], row["category"],
              f"[固定] {row['description'] or row['category']}"))

        # 更新最後執行日期
        cursor.execute("""
            UPDATE recurring_transactions
            SET last_executed = ?
            WHERE id = ?
        """, (today_str, row["id"]))

        executed_count += 1

    conn.commit()

    return executed_count


# ============ 習慣打卡相關函式 ============

def create_habit(user_id: str, name: str, emoji: str = '✓') -> int:
    """建立新習慣"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO habits (user_id, name, emoji)
        VALUES (?, ?, ?)
    """, (user_id, name, emoji))

    habit_id = cursor.lastrowid
    conn.commit()

    return habit_id


def get_habits(user_id: str) -> list:
    """取得用戶的所有習慣"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM habits
        WHERE user_id = ?
        ORDER BY created_at ASC
    """, (user_id,))

    rows = cursor.fetchall()

    return [dict_row(cursor, row) for row in rows]


def get_habit_by_id(habit_id: int, user_id: str) -> Optional[dict]:
    """取得單一習慣"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM habits
        WHERE id = ? AND user_id = ?
    """, (habit_id, user_id))

    row = cursor.fetchone()

    return dict_row(cursor, row) if row else None


def get_habit_by_name(user_id: str, name: str) -> Optional[dict]:
    """根據名稱取得習慣"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM habits
        WHERE user_id = ? AND name = ?
    """, (user_id, name))

    row = cursor.fetchone()

    return dict_row(cursor, row) if row else None


def update_habit(habit_id: int, user_id: str, name: str = None, emoji: str = None) -> bool:
    """更新習慣"""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if emoji is not None:
        updates.append("emoji = ?")
        params.append(emoji)

    if not updates:
            return True

    params.extend([habit_id, user_id])
    cursor.execute(f"""
        UPDATE habits
        SET {", ".join(updates)}
        WHERE id = ? AND user_id = ?
    """, params)

    updated = cursor.rowcount > 0
    conn.commit()

    return updated


def delete_habit(habit_id: int, user_id: str) -> bool:
    """刪除習慣（同時刪除打卡記錄）"""
    conn = get_connection()
    cursor = conn.cursor()

    # 刪除打卡記錄
    cursor.execute("""
        DELETE FROM habit_checkins WHERE habit_id = ? AND user_id = ?
    """, (habit_id, user_id))

    # 刪除習慣
    cursor.execute("""
        DELETE FROM habits WHERE id = ? AND user_id = ?
    """, (habit_id, user_id))

    deleted = cursor.rowcount > 0
    conn.commit()

    return deleted


def checkin_habit(user_id: str, habit_id: int, check_date: str = None) -> bool:
    """習慣打卡"""
    conn = get_connection()
    cursor = conn.cursor()

    if check_date is None:
        check_date = datetime.now().strftime("%Y-%m-%d")

    try:
        cursor.execute("""
            INSERT INTO habit_checkins (user_id, habit_id, check_date)
            VALUES (?, ?, ?)
        """, (user_id, habit_id, check_date))
        conn.commit()
        success = True
    except Exception:
        # 已經打卡過了
        success = False

    return success


def uncheckin_habit(user_id: str, habit_id: int, check_date: str = None) -> bool:
    """取消習慣打卡"""
    conn = get_connection()
    cursor = conn.cursor()

    if check_date is None:
        check_date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        DELETE FROM habit_checkins
        WHERE user_id = ? AND habit_id = ? AND check_date = ?
    """, (user_id, habit_id, check_date))

    deleted = cursor.rowcount > 0
    conn.commit()

    return deleted


def get_habit_checkins(user_id: str, habit_id: int, start_date: str = None, end_date: str = None) -> list:
    """取得習慣的打卡記錄"""
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["user_id = ?", "habit_id = ?"]
    params = [user_id, habit_id]

    if start_date:
        conditions.append("check_date >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("check_date <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    cursor.execute(f"""
        SELECT check_date FROM habit_checkins
        WHERE {where_clause}
        ORDER BY check_date DESC
    """, params)

    rows = cursor.fetchall()

    return [dict_row(cursor, row)["check_date"] for row in rows]


def get_today_checkins(user_id: str) -> list:
    """取得今日所有習慣的打卡狀態"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT h.*,
               CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END as checked
        FROM habits h
        LEFT JOIN habit_checkins c
            ON h.id = c.habit_id AND c.check_date = ? AND c.user_id = h.user_id
        WHERE h.user_id = ?
        ORDER BY h.created_at ASC
    """, (today, user_id))

    rows = cursor.fetchall()

    return [dict_row(cursor, row) for row in rows]


def get_habit_streak(user_id: str, habit_id: int) -> int:
    """計算連續打卡天數"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT check_date FROM habit_checkins
        WHERE user_id = ? AND habit_id = ?
        ORDER BY check_date DESC
    """, (user_id, habit_id))

    rows = cursor.fetchall()
    rows_dict = [dict_row(cursor, row) for row in rows]

    if not rows_dict:
        return 0

    streak = 0
    today = datetime.now().date()

    for row in rows_dict:
        check_date = datetime.strptime(row["check_date"], "%Y-%m-%d").date()
        expected_date = today - timedelta(days=streak)

        # 允許今天還沒打卡的情況
        if streak == 0 and check_date == today - timedelta(days=1):
            expected_date = today - timedelta(days=1)

        if check_date == expected_date:
            streak += 1
        elif streak == 0 and check_date == today:
            streak += 1
        else:
            break

    return streak


def get_habit_stats(user_id: str, habit_id: int, year: int = None, month: int = None) -> dict:
    """取得習慣統計"""
    conn = get_connection()
    cursor = conn.cursor()

    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    # 計算該月的天數
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    days_in_month = (next_month - datetime(year, month, 1)).days

    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{days_in_month:02d}"

    # 取得該月打卡天數
    cursor.execute("""
        SELECT COUNT(*) as count FROM habit_checkins
        WHERE user_id = ? AND habit_id = ? AND check_date >= ? AND check_date <= ?
    """, (user_id, habit_id, start_date, end_date))

    row = cursor.fetchone()
    result = dict_row(cursor, row)

    checked_days = result["count"]

    # 計算到今天為止的天數（如果是當月）
    today = datetime.now()
    if year == today.year and month == today.month:
        days_passed = today.day
    else:
        days_passed = days_in_month

    completion_rate = (checked_days / days_passed * 100) if days_passed > 0 else 0

    return {
        "year": year,
        "month": month,
        "checked_days": checked_days,
        "days_in_month": days_in_month,
        "days_passed": days_passed,
        "completion_rate": round(completion_rate, 1)
    }


# ============ 固定支出提醒相關函式 ============

def create_expense_reminder(
    user_id: str,
    name: str,
    amount: float,
    day_of_month: int
) -> int:
    """建立固定支出提醒"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO expense_reminders (user_id, name, amount, day_of_month)
        VALUES (?, ?, ?, ?)
    """, (user_id, name, amount, day_of_month))

    reminder_id = cursor.lastrowid
    conn.commit()

    return reminder_id


def get_expense_reminders(user_id: str) -> list:
    """取得用戶的所有固定支出提醒"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM expense_reminders
        WHERE user_id = ? AND is_active = 1
        ORDER BY day_of_month ASC
    """, (user_id,))

    rows = cursor.fetchall()

    return [dict_row(cursor, row) for row in rows]


def get_expense_reminder_by_id(reminder_id: int, user_id: str) -> Optional[dict]:
    """取得單筆固定支出提醒"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM expense_reminders
        WHERE id = ? AND user_id = ?
    """, (reminder_id, user_id))

    row = cursor.fetchone()

    return dict_row(cursor, row) if row else None


def update_expense_reminder(
    reminder_id: int,
    user_id: str,
    name: Optional[str] = None,
    amount: Optional[float] = None,
    day_of_month: Optional[int] = None,
    is_active: Optional[int] = None
) -> bool:
    """更新固定支出提醒"""
    conn = get_connection()
    cursor = conn.cursor()

    # 確認記錄存在
    cursor.execute("""
        SELECT id FROM expense_reminders WHERE id = ? AND user_id = ?
    """, (reminder_id, user_id))

    if not cursor.fetchone():
            return False

    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    if day_of_month is not None:
        updates.append("day_of_month = ?")
        params.append(day_of_month)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)

    if not updates:
            return True

    params.extend([reminder_id, user_id])
    cursor.execute(f"""
        UPDATE expense_reminders
        SET {", ".join(updates)}
        WHERE id = ? AND user_id = ?
    """, params)

    conn.commit()
    return True


def delete_expense_reminder(reminder_id: int, user_id: str) -> bool:
    """刪除固定支出提醒"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM expense_reminders WHERE id = ? AND user_id = ?
    """, (reminder_id, user_id))

    deleted = cursor.rowcount > 0
    conn.commit()

    return deleted


# ============ OAuth State 相關函式 ============

def save_oauth_state(state: str) -> bool:
    """儲存 OAuth state"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO oauth_states (state) VALUES (?)
        """, (state,))
        conn.commit()
        return True
    except Exception:
        return False


def verify_oauth_state(state: str) -> bool:
    """驗證並刪除 OAuth state"""
    conn = get_connection()
    cursor = conn.cursor()

    # 先檢查是否存在
    cursor.execute("""
        SELECT state FROM oauth_states WHERE state = ?
    """, (state,))

    row = cursor.fetchone()
    if not row:
        return False

    # 刪除已使用的 state
    cursor.execute("""
        DELETE FROM oauth_states WHERE state = ?
    """, (state,))
    conn.commit()

    return True


def cleanup_expired_states():
    """清理超過 10 分鐘的 state"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM oauth_states
        WHERE created_at < datetime('now', '-10 minutes')
    """)
    conn.commit()


# 初始化資料庫
init_db()
