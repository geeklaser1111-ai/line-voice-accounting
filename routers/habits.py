"""習慣打卡 API"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import (
    create_habit,
    get_habits,
    get_habit_by_id,
    get_habit_by_name,
    update_habit,
    delete_habit,
    checkin_habit,
    uncheckin_habit,
    get_habit_checkins,
    get_today_checkins,
    get_habit_streak,
    get_habit_stats
)

router = APIRouter(prefix="/api/habits", tags=["習慣打卡"])


def get_user_id(request: Request) -> str:
    """從 request 取得用戶 ID"""
    from routers.auth import get_user_id_from_request
    return get_user_id_from_request(request)


class HabitCreate(BaseModel):
    name: str
    emoji: Optional[str] = '✓'


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None


class CheckinRequest(BaseModel):
    date: Optional[str] = None


@router.get("")
async def list_habits(request: Request):
    """取得所有習慣及今日打卡狀態"""
    user_id = get_user_id(request)
    habits = get_today_checkins(user_id)

    # 加入連續天數
    for habit in habits:
        habit["streak"] = get_habit_streak(user_id, habit["id"])

    return {"items": habits}


@router.post("")
async def create_new_habit(request: Request, data: HabitCreate):
    """建立新習慣"""
    user_id = get_user_id(request)

    # 檢查是否已存在同名習慣
    existing = get_habit_by_name(user_id, data.name)
    if existing:
        raise HTTPException(status_code=400, detail="習慣已存在")

    habit_id = create_habit(user_id, data.name, data.emoji or '✓')

    return {
        "id": habit_id,
        "name": data.name,
        "emoji": data.emoji or '✓',
        "message": "習慣建立成功"
    }


@router.get("/{habit_id}")
async def get_single_habit(request: Request, habit_id: int):
    """取得單一習慣詳情"""
    user_id = get_user_id(request)
    habit = get_habit_by_id(habit_id, user_id)

    if not habit:
        raise HTTPException(status_code=404, detail="習慣不存在")

    habit["streak"] = get_habit_streak(user_id, habit_id)

    return habit


@router.put("/{habit_id}")
async def update_single_habit(request: Request, habit_id: int, data: HabitUpdate):
    """更新習慣"""
    user_id = get_user_id(request)

    if not get_habit_by_id(habit_id, user_id):
        raise HTTPException(status_code=404, detail="習慣不存在")

    success = update_habit(habit_id, user_id, data.name, data.emoji)

    if not success:
        raise HTTPException(status_code=500, detail="更新失敗")

    return {"message": "更新成功"}


@router.delete("/{habit_id}")
async def delete_single_habit(request: Request, habit_id: int):
    """刪除習慣"""
    user_id = get_user_id(request)

    success = delete_habit(habit_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="習慣不存在")

    return {"message": "刪除成功"}


@router.post("/{habit_id}/checkin")
async def checkin(request: Request, habit_id: int, data: CheckinRequest = None):
    """打卡"""
    user_id = get_user_id(request)

    if not get_habit_by_id(habit_id, user_id):
        raise HTTPException(status_code=404, detail="習慣不存在")

    check_date = data.date if data else None
    success = checkin_habit(user_id, habit_id, check_date)

    if not success:
        return {"message": "今天已經打卡過了", "already_checked": True}

    streak = get_habit_streak(user_id, habit_id)

    return {
        "message": "打卡成功",
        "already_checked": False,
        "streak": streak
    }


@router.delete("/{habit_id}/checkin")
async def cancel_checkin(request: Request, habit_id: int, date: Optional[str] = None):
    """取消打卡"""
    user_id = get_user_id(request)

    success = uncheckin_habit(user_id, habit_id, date)

    if not success:
        raise HTTPException(status_code=404, detail="找不到打卡記錄")

    return {"message": "已取消打卡"}


@router.get("/{habit_id}/checkins")
async def get_checkins(
    request: Request,
    habit_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """取得打卡記錄"""
    user_id = get_user_id(request)

    if not get_habit_by_id(habit_id, user_id):
        raise HTTPException(status_code=404, detail="習慣不存在")

    checkins = get_habit_checkins(user_id, habit_id, start_date, end_date)

    return {"dates": checkins}


@router.get("/{habit_id}/stats")
async def get_stats(
    request: Request,
    habit_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """取得習慣統計"""
    user_id = get_user_id(request)

    if not get_habit_by_id(habit_id, user_id):
        raise HTTPException(status_code=404, detail="習慣不存在")

    stats = get_habit_stats(user_id, habit_id, year, month)
    stats["streak"] = get_habit_streak(user_id, habit_id)

    return stats
