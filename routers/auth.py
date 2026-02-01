"""LINE Login 認證 API"""
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from services.line_login import (
    generate_state,
    get_login_url,
    exchange_code_for_token,
    get_user_profile
)
from database import create_session, get_session, delete_session, save_oauth_state, verify_oauth_state
from config import SESSION_COOKIE_NAME

router = APIRouter(prefix="/auth", tags=["認證"])


@router.get("/login")
async def login(request: Request):
    """導向 LINE Login 頁面"""
    state = generate_state()
    save_oauth_state(state)  # 存到資料庫

    login_url = get_login_url(state)
    return RedirectResponse(url=login_url)


@router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    """LINE Login 回調"""
    # 檢查錯誤
    if error:
        return RedirectResponse(url=f"/static/index.html?error={error}")

    # 驗證 state（從資料庫）
    if not state or not verify_oauth_state(state):
        return RedirectResponse(url="/static/index.html?error=invalid_state")

    # 交換 token
    token_data = await exchange_code_for_token(code)
    if not token_data:
        return RedirectResponse(url="/static/index.html?error=token_exchange_failed")

    # 取得用戶資料
    access_token = token_data.get("access_token")
    profile = await get_user_profile(access_token)
    if not profile:
        return RedirectResponse(url="/static/index.html?error=profile_fetch_failed")

    # 建立 session
    user_id = profile.get("userId")
    display_name = profile.get("displayName", "")
    picture_url = profile.get("pictureUrl", "")

    session_id = create_session(user_id, display_name, picture_url)

    # 設定 cookie 並導向儀表板
    response = RedirectResponse(url="/static/dashboard.html")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=True,  # HTTPS 必須
        max_age=7 * 24 * 60 * 60,  # 7 天
        samesite="lax"
    )

    return response


@router.post("/logout")
async def logout(request: Request, response: Response):
    """登出"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if session_id:
        delete_session(session_id)

    response = Response(content='{"status": "ok"}', media_type="application/json")
    response.delete_cookie(key=SESSION_COOKIE_NAME)

    return response


@router.get("/me")
async def get_current_user(request: Request):
    """取得當前登入用戶"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_id:
        raise HTTPException(status_code=401, detail="未登入")

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session 已過期")

    return {
        "user_id": session["user_id"],
        "display_name": session["display_name"],
        "picture_url": session["picture_url"]
    }


def get_user_id_from_request(request: Request) -> str:
    """從 request 取得用戶 ID（供其他 router 使用）"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_id:
        raise HTTPException(status_code=401, detail="未登入")

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session 已過期")

    return session["user_id"]
