"""交易 CRUD API"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import (
    get_transactions_paginated,
    get_transaction_by_id,
    add_transaction,
    update_transaction,
    delete_transaction,
    get_categories
)
from routers.auth import get_user_id_from_request

router = APIRouter(prefix="/api/transactions", tags=["交易"])


class TransactionCreate(BaseModel):
    type: str  # income / expense
    amount: float
    category: str
    description: Optional[str] = None


class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None


@router.get("")
async def list_transactions(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """取得交易列表（分頁、篩選）"""
    user_id = get_user_id_from_request(request)

    result = get_transactions_paginated(
        user_id=user_id,
        page=page,
        per_page=per_page,
        trans_type=type,
        category=category,
        start_date=start_date,
        end_date=end_date
    )

    return result


@router.get("/categories")
async def list_categories(request: Request):
    """取得用戶的所有分類"""
    user_id = get_user_id_from_request(request)
    categories = get_categories(user_id)
    return {"categories": categories}


@router.get("/{transaction_id}")
async def get_transaction(request: Request, transaction_id: int):
    """取得單筆交易"""
    user_id = get_user_id_from_request(request)

    transaction = get_transaction_by_id(transaction_id, user_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="交易記錄不存在")

    return transaction


@router.post("")
async def create_transaction(request: Request, data: TransactionCreate):
    """新增交易"""
    user_id = get_user_id_from_request(request)

    # 驗證類型
    if data.type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="類型必須是 income 或 expense")

    # 驗證金額
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="金額必須大於 0")

    transaction_id = add_transaction(
        user_id=user_id,
        trans_type=data.type,
        amount=data.amount,
        category=data.category,
        description=data.description
    )

    return {
        "id": transaction_id,
        "message": "新增成功"
    }


@router.put("/{transaction_id}")
async def update_transaction_endpoint(
    request: Request,
    transaction_id: int,
    data: TransactionUpdate
):
    """更新交易"""
    user_id = get_user_id_from_request(request)

    # 驗證類型
    if data.type and data.type not in ["income", "expense"]:
        raise HTTPException(status_code=400, detail="類型必須是 income 或 expense")

    # 驗證金額
    if data.amount is not None and data.amount <= 0:
        raise HTTPException(status_code=400, detail="金額必須大於 0")

    success = update_transaction(
        transaction_id=transaction_id,
        user_id=user_id,
        trans_type=data.type,
        amount=data.amount,
        category=data.category,
        description=data.description
    )

    if not success:
        raise HTTPException(status_code=404, detail="交易記錄不存在")

    return {"message": "更新成功"}


@router.delete("/{transaction_id}")
async def delete_transaction_endpoint(request: Request, transaction_id: int):
    """刪除交易"""
    user_id = get_user_id_from_request(request)

    success = delete_transaction(transaction_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="交易記錄不存在")

    return {"message": "刪除成功"}
