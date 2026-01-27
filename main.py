from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, AudioMessageContent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from voice_handler import process_voice_message
from parser import parse_transaction
from database import add_transaction, get_summary
from datetime import date

# 引入路由
from routers import auth, transactions, stats, export

app = FastAPI(title="LINE 語音記帳機器人")

# 註冊路由
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(stats.router)
app.include_router(export.router)

# 掛載靜態檔案
app.mount("/static", StaticFiles(directory="static"), name="static")

# LINE Bot 設定
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@app.get("/")
async def root():
    """首頁導向"""
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health():
    """健康檢查"""
    return {"status": "ok", "message": "LINE 語音記帳機器人運作中"}


@app.post("/webhook")
async def webhook(request: Request):
    """LINE Webhook 端點"""
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_text = body.decode("utf-8")

    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return {"status": "ok"}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    """處理文字訊息"""
    user_id = event.source.user_id
    text = event.message.text.strip()

    reply_text = None

    # 今日收支查詢
    if text == "今日收支":
        today = date.today().isoformat()
        summary = get_summary(user_id, start_date=today, end_date=today)

        reply_text = (
            f"📊 今日收支報告\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 收入：${summary['total_income']:,.0f}\n"
            f"💸 支出：${summary['total_expense']:,.0f}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📈 結餘：${summary['balance']:,.0f}\n"
            f"📝 筆數：{summary['transaction_count']} 筆\n\n"
            f"🌐 查看更多：\n"
            f"https://line-voice-accounting.onrender.com"
        )

    # 如果有回覆內容才回覆
    if reply_text:
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )


@handler.add(MessageEvent, message=AudioMessageContent)
def handle_audio_message(event: MessageEvent):
    """處理語音訊息"""
    user_id = event.source.user_id
    message_id = event.message.id

    try:
        # 1. 語音轉文字
        text = process_voice_message(message_id)
        print(f"語音辨識結果: {text}")

        # 2. 解析記帳內容
        parsed = parse_transaction(text)

        if parsed is None:
            reply_text = f"抱歉，無法解析記帳內容。\n\n語音辨識結果：{text}\n\n請嘗試說清楚金額，例如「午餐 150」"
        else:
            # 3. 儲存到資料庫
            transaction_id = add_transaction(
                user_id=user_id,
                trans_type=parsed.type,
                amount=parsed.amount,
                category=parsed.category,
                description=parsed.description
            )

            # 4. 回覆確認訊息
            type_text = "收入" if parsed.type == "income" else "支出"
            reply_text = (
                f"記帳成功！\n\n"
                f"類型：{type_text}\n"
                f"分類：{parsed.category}\n"
                f"金額：${parsed.amount:,.0f}\n"
                f"描述：{parsed.description}"
            )

    except Exception as e:
        print(f"處理錯誤: {e}")
        reply_text = f"處理時發生錯誤，請稍後再試。\n錯誤：{str(e)}"

    # 回覆訊息
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
