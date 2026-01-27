"""統計 API"""
from fastapi import APIRouter, Request
from typing import Optional
from database import (
    get_summary,
    get_stats_by_category,
    get_stats_by_date
)
from routers.auth import get_user_id_from_request

router = APIRouter(prefix="/api/stats", tags=["統計"])


@router.get("/summary")
async def get_stats_summary(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """取得總收入、支出、餘額"""
    user_id = get_user_id_from_request(request)

    summary = get_summary(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    return summary


@router.get("/by-category")
async def get_category_stats(
    request: Request,
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """取得分類統計"""
    user_id = get_user_id_from_request(request)

    stats = get_stats_by_category(
        user_id=user_id,
        trans_type=type,
        start_date=start_date,
        end_date=end_date
    )

    return {"categories": stats}


@router.get("/by-date")
async def get_date_stats(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day"
):
    """取得日期趨勢統計"""
    user_id = get_user_id_from_request(request)

    # 驗證 group_by 參數
    if group_by not in ["day", "week", "month"]:
        group_by = "day"

    stats = get_stats_by_date(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )

    return {"trends": stats}
