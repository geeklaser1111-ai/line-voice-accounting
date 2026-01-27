"""預算設定 API"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from database import get_budget, set_budget, get_budget_status
from routers.auth import get_user_id_from_request

router = APIRouter(prefix="/api/budget", tags=["預算"])


class BudgetCreate(BaseModel):
    monthly_budget: float


@router.get("")
async def get_user_budget(request: Request):
    """取得預算設定"""
    user_id = get_user_id_from_request(request)
    budget = get_budget(user_id)

    if not budget:
        return {"monthly_budget": 0}

    return {"monthly_budget": budget["monthly_budget"]}


@router.post("")
async def set_user_budget(request: Request, data: BudgetCreate):
    """設定每月預算"""
    user_id = get_user_id_from_request(request)

    if data.monthly_budget < 0:
        raise HTTPException(status_code=400, detail="預算不能為負數")

    budget_id = set_budget(user_id, data.monthly_budget)

    return {"id": budget_id, "message": "預算設定成功"}


@router.get("/status")
async def get_user_budget_status(request: Request):
    """取得預算使用狀況"""
    user_id = get_user_id_from_request(request)
    status = get_budget_status(user_id)

    return status
