"""固定收支 API"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import (
    add_recurring_transaction,
    get_recurring_transactions,
    get_recurring_transaction_by_id,
    update_recurring_transaction,
    delete_recurring_transaction,
    execute_recurring_transactions
)
import os
from routers.auth import get_user_id_from_request

router = APIRouter(prefix="/api/recurring", tags=["固定收支"])

# 用於驗證 cron job 的密鑰
CRON_SECRET = os.getenv("CRON_SECRET", "your-secret-key")


class RecurringCreate(BaseModel):
    type: str  # income / expense
    amount: float
    category: str
    description: Optional[str] = None
    day_of_month: int = 1  # 每月幾號執行


class RecurringUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    day_of_month: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_recurring(request: Request):
    """取得固定收支列表"""
    user_id = get_user_id_from_request(request)
    items = get_recurring_transactions(user_id)

    return {"items": items}


@router.get("/{recurring_id}")
async def get_recurring(request: Request, recurring_id: int):
    """取得單筆固定收支"""
    user_id = get_user_id_from_request(request)
    item = get_recurring_transaction_by_id(recurring_id, user_id)

    if not item:
        raise HTTPException(status_code=404, detail="找不到此固定收支")

    return item


@router.post("")
async def create_recurring(request: Request, data: RecurringCreate):
    """新增固定收支"""
    user_id = get_user_id_from_request(request)

    # 驗證
    if data.type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="類型必須是 income 或 expense")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="金額必須大於 0")

    if data.day_of_month < 1 or data.day_of_month > 28:
        raise HTTPException(status_code=400, detail="執行日期必須在 1-28 之間")

    recurring_id = add_recurring_transaction(
        user_id=user_id,
        trans_type=data.type,
        amount=data.amount,
        category=data.category,
        description=data.description,
        day_of_month=data.day_of_month
    )

    return {"id": recurring_id, "message": "新增成功"}


@router.put("/{recurring_id}")
async def update_recurring_endpoint(request: Request, recurring_id: int, data: RecurringUpdate):
    """更新固定收支"""
    user_id = get_user_id_from_request(request)

    # 驗證
    if data.type and data.type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="類型必須是 income 或 expense")

    if data.amount is not None and data.amount <= 0:
        raise HTTPException(status_code=400, detail="金額必須大於 0")

    if data.day_of_month is not None and (data.day_of_month < 1 or data.day_of_month > 28):
        raise HTTPException(status_code=400, detail="執行日期必須在 1-28 之間")

    is_active = 1 if data.is_active else 0 if data.is_active is not None else None

    success = update_recurring_transaction(
        recurring_id=recurring_id,
        user_id=user_id,
        trans_type=data.type,
        amount=data.amount,
        category=data.category,
        description=data.description,
        day_of_month=data.day_of_month,
        is_active=is_active
    )

    if not success:
        raise HTTPException(status_code=404, detail="找不到此固定收支")

    return {"message": "更新成功"}


@router.delete("/{recurring_id}")
async def delete_recurring_endpoint(request: Request, recurring_id: int):
    """刪除固定收支"""
    user_id = get_user_id_from_request(request)

    success = delete_recurring_transaction(recurring_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="找不到此固定收支")

    return {"message": "刪除成功"}


@router.post("/execute")
async def execute_recurring_endpoint(request: Request, secret: str = None):
    """
    執行今天的固定收支（由 Cron Job 呼叫）
    需要提供正確的 secret 參數
    """
    # 驗證密鑰
    if secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="無效的密鑰")

    # 執行固定收支
    executed_count = execute_recurring_transactions()

    return {
        "message": f"已執行 {executed_count} 筆固定收支",
        "executed_count": executed_count
    }
