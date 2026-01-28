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
    QuickReply,
    QuickReplyItem,
    MessageAction,
    URIAction,
)
from linebot.v3.webhooks import MessageEvent, AudioMessageContent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
from voice_handler import process_voice_message
from parser import parse_transaction
from database import add_transaction, get_summary
from datetime import date

# 引入路由
from routers import auth, transactions, stats, export, budget, recurring, energy, habits

app = FastAPI(title="LINE 語音記帳機器人")

# 註冊路由
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(stats.router)
app.include_router(export.router)
app.include_router(budget.router)
app.include_router(recurring.router)
app.include_router(energy.router)
app.include_router(habits.router)

# 掛載靜態檔案
app.mount("/static", StaticFiles(directory="static"), name="static")

# LINE Bot 設定
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


def get_quick_reply():
    """取得常駐的快速回覆按鈕"""
    return QuickReply(
        items=[
            QuickReplyItem(
                action=MessageAction(label="今日收支", text="今日收支")
            ),
            QuickReplyItem(
                action=MessageAction(label="習慣", text="習慣")
            ),
            QuickReplyItem(
                action=MessageAction(label="能量幣", text="能量幣")
            ),
            QuickReplyItem(
                action=URIAction(label="查看網頁版", uri="https://line-voice-accounting.onrender.com")
            ),
            QuickReplyItem(
                action=MessageAction(label="使用說明", text="使用說明")
            ),
        ]
    )


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

    # 使用說明
    if text == "使用說明":
        reply_text = (
            f"📝 語音記帳使用說明\n"
            f"━━━━━━━━━━━━━━\n"
            f"【記帳方式】\n"
            f"• 語音：直接說「午餐 150」\n"
            f"• 文字：輸入「午餐 150」\n"
            f"• 收入：輸入「收入 薪水 50000」\n\n"
            f"【查看記錄】\n"
            f"• 輸入「今日收支」\n"
            f"• 網頁版：\n"
            f"line-voice-accounting.onrender.com"
        )
    # 今日收支查詢
    elif text == "今日收支":
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
    # 能量幣查詢
    elif text == "能量幣":
        from routers.energy import get_user_energy_coins
        coins = get_user_energy_coins(user_id)

        reply_text = (
            f"✨ 能量幣報告\n"
            f"━━━━━━━━━━━━━━\n"
            f"🥇 金幣：{coins['gold']} 枚\n"
            f"   └ 還債累計 ${coins['gold_amount']:,.0f}\n"
            f"🥈 銀幣：{coins['silver']} 枚\n"
            f"   └ 捐款累計 ${coins['silver_amount']:,.0f}\n"
            f"🥉 銅幣：{coins['copper']} 枚\n"
            f"   └ 打工累計 ${coins['copper_amount']:,.0f}\n"
            f"━━━━━━━━━━━━━━\n"
            f"🏆 總能量幣：{coins['total_coins']} 枚\n\n"
            f"🌐 查看詳情：\n"
            f"https://line-voice-accounting.onrender.com/static/energy.html"
        )
    # 習慣查詢
    elif text == "習慣":
        from database import get_today_checkins, get_habit_streak
        habits_status = get_today_checkins(user_id)

        if not habits_status:
            reply_text = (
                f"📋 習慣追蹤\n"
                f"━━━━━━━━━━━━━━\n"
                f"尚未建立任何習慣\n\n"
                f"輸入「新增習慣 打拳」來建立\n"
                f"或到網頁版管理習慣：\n"
                f"https://line-voice-accounting.onrender.com/static/habits.html"
            )
        else:
            lines = ["📋 今日習慣\n━━━━━━━━━━━━━━"]
            for h in habits_status:
                status = "✅" if h["checked"] else "⬜"
                streak = get_habit_streak(user_id, h["id"])
                streak_text = f" 🔥{streak}天" if streak > 0 else ""
                lines.append(f"{status} {h['emoji']} {h['name']}{streak_text}")

            lines.append(f"\n輸入習慣名稱即可打卡")
            lines.append(f"例如：打拳")
            reply_text = "\n".join(lines)

    # 新增習慣
    elif text.startswith("新增習慣 ") or text.startswith("新增習慣"):
        from database import create_habit, get_habit_by_name
        habit_name = text.replace("新增習慣", "").strip()

        if not habit_name:
            reply_text = "請輸入習慣名稱\n例如：新增習慣 打拳"
        elif get_habit_by_name(user_id, habit_name):
            reply_text = f"「{habit_name}」習慣已存在"
        else:
            create_habit(user_id, habit_name)
            reply_text = (
                f"✅ 習慣建立成功！\n\n"
                f"習慣名稱：{habit_name}\n\n"
                f"輸入「{habit_name}」即可打卡"
            )

    # 打卡習慣（直接輸入習慣名稱或「打卡 習慣名稱」）
    elif text.startswith("打卡 "):
        from database import get_habit_by_name, checkin_habit, get_habit_streak
        habit_name = text.replace("打卡 ", "").strip()
        habit = get_habit_by_name(user_id, habit_name)

        if not habit:
            reply_text = f"找不到「{habit_name}」習慣\n\n輸入「習慣」查看所有習慣"
        else:
            success = checkin_habit(user_id, habit["id"])
            streak = get_habit_streak(user_id, habit["id"])

            if success:
                reply_text = (
                    f"✅ {habit['emoji']} {habit_name} 打卡成功！\n\n"
                    f"🔥 連續 {streak} 天\n\n"
                    f"繼續保持！💪"
                )
            else:
                reply_text = f"今天「{habit_name}」已經打卡過了！\n\n🔥 連續 {streak} 天"

    else:
        # 先檢查是否為「日期 + 習慣」格式（補打）
        from database import get_habit_by_name, checkin_habit, get_habit_streak
        import re
        from datetime import datetime, timedelta

        check_date = None
        habit_name = None
        date_display = None

        # 解析日期格式
        # 昨天/前天 + 習慣
        if text.startswith("昨天 ") or text.startswith("昨天"):
            habit_name = text.replace("昨天", "").strip()
            check_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            date_display = "昨天"
        elif text.startswith("前天 ") or text.startswith("前天"):
            habit_name = text.replace("前天", "").strip()
            check_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            date_display = "前天"
        else:
            # M/D 或 MM/DD 或 YYYY/M/D 格式
            date_match = re.match(r'^(\d{4}/)?(\d{1,2})/(\d{1,2})\s+(.+)$', text)
            if date_match:
                year = int(date_match.group(1)[:-1]) if date_match.group(1) else datetime.now().year
                month = int(date_match.group(2))
                day = int(date_match.group(3))
                habit_name = date_match.group(4).strip()
                try:
                    check_date = f"{year}-{month:02d}-{day:02d}"
                    # 驗證日期有效
                    datetime.strptime(check_date, "%Y-%m-%d")
                    date_display = f"{month}/{day}"
                except ValueError:
                    check_date = None

        # 如果有解析到日期和習慣名稱，嘗試補打
        if check_date and habit_name:
            habit = get_habit_by_name(user_id, habit_name)
            if habit:
                success = checkin_habit(user_id, habit["id"], check_date)
                streak = get_habit_streak(user_id, habit["id"])

                if success:
                    reply_text = (
                        f"✅ {habit['emoji']} {habit_name} 補打成功！\n\n"
                        f"📅 日期：{date_display}\n"
                        f"🔥 連續 {streak} 天\n\n"
                        f"繼續保持！💪"
                    )
                else:
                    reply_text = f"「{habit_name}」在 {date_display} 已經打卡過了！"
            else:
                # 習慣不存在，可能是記帳，繼續往下處理
                pass

        if reply_text is None:
            # 先檢查是否為習慣名稱（直接打卡）
            habit = get_habit_by_name(user_id, text)

            if habit:
                success = checkin_habit(user_id, habit["id"])
                streak = get_habit_streak(user_id, habit["id"])

                if success:
                    reply_text = (
                        f"✅ {habit['emoji']} {habit['name']} 打卡成功！\n\n"
                        f"🔥 連續 {streak} 天\n\n"
                        f"繼續保持！💪"
                    )
                else:
                    reply_text = f"今天「{habit['name']}」已經打卡過了！\n\n🔥 連續 {streak} 天"
            else:
                # 嘗試解析為記帳內容
                parsed = parse_transaction(text)

                if parsed:
                    # 儲存到資料庫
                    transaction_id = add_transaction(
                        user_id=user_id,
                        trans_type=parsed.type,
                        amount=parsed.amount,
                        category=parsed.category,
                        description=parsed.description
                    )

                    # 回覆確認訊息
                    type_text = "收入" if parsed.type == "income" else "支出"
                    reply_text = (
                        f"✅ 記帳成功！\n\n"
                        f"類型：{type_text}\n"
                        f"分類：{parsed.category}\n"
                        f"金額：${parsed.amount:,.0f}\n"
                        f"描述：{parsed.description}"
                    )
                else:
                    # 無法解析，顯示使用說明
                    reply_text = (
                        f"📝 記帳小幫手\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"請輸入記帳內容，例如：\n"
                        f"• 午餐 150\n"
                        f"• 交通費 50\n"
                        f"• 收入 薪水 50000\n\n"
                        f"或使用語音輸入更方便！"
                    )

    # 回覆訊息（帶快速回覆按鈕）
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text, quick_reply=get_quick_reply())]
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

    # 回覆訊息（帶快速回覆按鈕）
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text, quick_reply=get_quick_reply())]
            )
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
