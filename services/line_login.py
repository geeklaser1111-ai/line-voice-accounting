"""LINE Login OAuth 2.0 服務"""
import secrets
import httpx
from urllib.parse import urlencode
from typing import Optional
from config import (
    LINE_LOGIN_CHANNEL_ID,
    LINE_LOGIN_CHANNEL_SECRET,
    LINE_LOGIN_REDIRECT_URI
)

LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"


def generate_state() -> str:
    """產生隨機 state 防止 CSRF"""
    return secrets.token_urlsafe(32)


def get_login_url(state: str) -> str:
    """取得 LINE Login 授權 URL"""
    params = {
        "response_type": "code",
        "client_id": LINE_LOGIN_CHANNEL_ID,
        "redirect_uri": LINE_LOGIN_REDIRECT_URI,
        "state": state,
        "scope": "profile openid",
    }
    return f"{LINE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> Optional[dict]:
    """用授權碼交換 access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LINE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINE_LOGIN_REDIRECT_URI,
                "client_id": LINE_LOGIN_CHANNEL_ID,
                "client_secret": LINE_LOGIN_CHANNEL_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            print(f"Token exchange failed: {response.text}")
            return None

        return response.json()


async def get_user_profile(access_token: str) -> Optional[dict]:
    """取得用戶資料"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            LINE_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if response.status_code != 200:
            print(f"Get profile failed: {response.text}")
            return None

        return response.json()
