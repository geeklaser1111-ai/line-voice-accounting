"""固定支出提醒 API"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

from database import (
    create_expense_reminder,
    get_expense_reminders,
    get_expense_reminder_by_id,
    update_expense_reminder,
    delete_expense_reminder
)

router = APIRouter(prefix="/api/reminders", tags=["固定支出提醒"])


def get_user_id(request: Request) -> str:
    """從 request 取得用戶 ID"""
    from routers.auth import get_user_id_from_request
    return get_user_id_from_request(request)


class ReminderCreate(BaseModel):
    name: str
    amount: float
    day_of_month: int


class ReminderUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    day_of_month: Optional[int] = None


@router.get("")
async def list_reminders(request: Request):
    """取得所有固定支出提醒"""
    user_id = get_user_id(request)
    reminders = get_expense_reminders(user_id)

    # 計算總額
    total = sum(r["amount"] for r in reminders)

    return {
        "items": reminders,
        "total": total
    }


@router.post("")
async def create_new_reminder(request: Request, data: ReminderCreate):
    """建立新的固定支出提醒"""
    user_id = get_user_id(request)

    # 驗證 day_of_month
    if data.day_of_month < 1 or data.day_of_month > 28:
        raise HTTPException(status_code=400, detail="日期必須在 1-28 之間")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="金額必須大於 0")

    reminder_id = create_expense_reminder(
        user_id,
        data.name,
        data.amount,
        data.day_of_month
    )

    return {
        "id": reminder_id,
        "name": data.name,
        "amount": data.amount,
        "day_of_month": data.day_of_month,
        "message": "提醒建立成功"
    }


@router.get("/{reminder_id}")
async def get_single_reminder(request: Request, reminder_id: int):
    """取得單一固定支出提醒"""
    user_id = get_user_id(request)
    reminder = get_expense_reminder_by_id(reminder_id, user_id)

    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")

    return reminder


@router.put("/{reminder_id}")
async def update_single_reminder(request: Request, reminder_id: int, data: ReminderUpdate):
    """更新固定支出提醒"""
    user_id = get_user_id(request)

    if not get_expense_reminder_by_id(reminder_id, user_id):
        raise HTTPException(status_code=404, detail="提醒不存在")

    # 驗證 day_of_month
    if data.day_of_month is not None:
        if data.day_of_month < 1 or data.day_of_month > 28:
            raise HTTPException(status_code=400, detail="日期必須在 1-28 之間")

    if data.amount is not None and data.amount <= 0:
        raise HTTPException(status_code=400, detail="金額必須大於 0")

    success = update_expense_reminder(
        reminder_id,
        user_id,
        data.name,
        data.amount,
        data.day_of_month
    )

    if not success:
        raise HTTPException(status_code=500, detail="更新失敗")

    return {"message": "更新成功"}


@router.delete("/{reminder_id}")
async def delete_single_reminder(request: Request, reminder_id: int):
    """刪除固定支出提醒"""
    user_id = get_user_id(request)

    success = delete_expense_reminder(reminder_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="提醒不存在")

    return {"message": "刪除成功"}
