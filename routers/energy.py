"""
能量幣 API
規則：
- 金幣：還債/還貸款/還錢 - 每100元 = 1金幣
- 銀幣：捐款 - 每100元 = 1銀幣
- 銅幣：打工收入 - 每100元 = 1銅幣
"""
from fastapi import APIRouter, Request
from typing import Optional

from database import get_connection
from routers.auth import get_user_id_from_request

router = APIRouter(prefix="/api/energy", tags=["能量幣"])

# 關鍵字定義
GOLD_KEYWORDS = ['還債', '還貸', '還款', '還錢', '償還', '貸款', '債務', '借款', '還清']
SILVER_KEYWORDS = ['捐款', '捐贈', '慈善', '公益', '愛心', '捐助', '樂捐']
COPPER_KEYWORDS = ['打工', '兼職', '時薪', '工讀', '臨時工', '零工', '外快', '副業']


def calculate_coins(transactions: list) -> dict:
    """計算能量幣"""
    gold = 0
    silver = 0
    copper = 0

    gold_amount = 0
    silver_amount = 0
    copper_amount = 0

    gold_transactions = []
    silver_transactions = []
    copper_transactions = []

    for t in transactions:
        category = (t.get('category') or '').lower()
        description = (t.get('description') or '').lower()
        combined = category + ' ' + description
        amount = t.get('amount', 0)
        trans_type = t.get('type', '')

        # 金幣：還債相關（支出類型）
        if trans_type == 'expense':
            for keyword in GOLD_KEYWORDS:
                if keyword in combined:
                    gold_amount += amount
                    gold_transactions.append(t)
                    break

        # 銀幣：捐款相關（支出類型）
        if trans_type == 'expense':
            for keyword in SILVER_KEYWORDS:
                if keyword in combined:
                    silver_amount += amount
                    silver_transactions.append(t)
                    break

        # 銅幣：打工相關（收入類型）
        if trans_type == 'income':
            for keyword in COPPER_KEYWORDS:
                if keyword in combined:
                    copper_amount += amount
                    copper_transactions.append(t)
                    break

    # 計算幣數（每100元 = 1幣）
    gold = int(gold_amount // 100)
    silver = int(silver_amount // 100)
    copper = int(copper_amount // 100)

    return {
        'gold': gold,
        'silver': silver,
        'copper': copper,
        'gold_amount': gold_amount,
        'silver_amount': silver_amount,
        'copper_amount': copper_amount,
        'total_coins': gold + silver + copper,
        'gold_transactions_count': len(gold_transactions),
        'silver_transactions_count': len(silver_transactions),
        'copper_transactions_count': len(copper_transactions),
    }


@router.get("")
async def get_energy_coins(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """取得能量幣統計"""
    user_id = get_user_id_from_request(request)

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

    transactions = [dict(row) for row in rows]
    coins = calculate_coins(transactions)

    return coins


@router.get("/history")
async def get_energy_history(
    request: Request,
    coin_type: str = "all",
    limit: int = 20
):
    """取得能量幣相關交易記錄"""
    user_id = get_user_id_from_request(request)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    transactions = [dict(row) for row in rows]

    # 過濾相關交易
    result = []
    for t in transactions:
        category = (t.get('category') or '').lower()
        description = (t.get('description') or '').lower()
        combined = category + ' ' + description
        trans_type = t.get('type', '')

        coin_earned = None

        # 金幣
        if coin_type in ['all', 'gold'] and trans_type == 'expense':
            for keyword in GOLD_KEYWORDS:
                if keyword in combined:
                    coin_earned = {'type': 'gold', 'amount': int(t['amount'] // 100)}
                    break

        # 銀幣
        if coin_type in ['all', 'silver'] and trans_type == 'expense' and not coin_earned:
            for keyword in SILVER_KEYWORDS:
                if keyword in combined:
                    coin_earned = {'type': 'silver', 'amount': int(t['amount'] // 100)}
                    break

        # 銅幣
        if coin_type in ['all', 'copper'] and trans_type == 'income' and not coin_earned:
            for keyword in COPPER_KEYWORDS:
                if keyword in combined:
                    coin_earned = {'type': 'copper', 'amount': int(t['amount'] // 100)}
                    break

        if coin_earned and coin_earned['amount'] > 0:
            t['coin'] = coin_earned
            result.append(t)

        if len(result) >= limit:
            break

    return {'items': result}


def get_user_energy_coins(user_id: str) -> dict:
    """取得用戶的能量幣（供 LINE Bot 使用）"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM transactions
        WHERE user_id = ?
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    transactions = [dict(row) for row in rows]
    return calculate_coins(transactions)
