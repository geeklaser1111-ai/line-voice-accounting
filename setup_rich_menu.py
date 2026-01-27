"""
設定 LINE Rich Menu（圖文選單）
執行一次即可：python setup_rich_menu.py
"""
import json
import httpx
from config import LINE_CHANNEL_ACCESS_TOKEN

BASE_URL = "https://api.line.me/v2/bot"
HEADERS = {
    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Rich Menu 設定
RICH_MENU = {
    "size": {
        "width": 2500,
        "height": 843
    },
    "selected": True,  # 預設展開
    "name": "語音記帳選單",
    "chatBarText": "點我開啟選單",
    "areas": [
        {
            # 左邊按鈕：今日收支
            "bounds": {
                "x": 0,
                "y": 0,
                "width": 1250,
                "height": 843
            },
            "action": {
                "type": "message",
                "text": "今日收支"
            }
        },
        {
            # 右邊按鈕：查看網頁版
            "bounds": {
                "x": 1250,
                "y": 0,
                "width": 1250,
                "height": 843
            },
            "action": {
                "type": "uri",
                "uri": "https://line-voice-accounting.onrender.com"
            }
        }
    ]
}


def create_rich_menu():
    """建立 Rich Menu"""
    response = httpx.post(
        f"{BASE_URL}/richmenu",
        headers=HEADERS,
        json=RICH_MENU
    )

    if response.status_code != 200:
        print(f"建立失敗: {response.text}")
        return None

    rich_menu_id = response.json()["richMenuId"]
    print(f"Rich Menu 建立成功！ID: {rich_menu_id}")
    return rich_menu_id


def upload_rich_menu_image(rich_menu_id: str):
    """上傳 Rich Menu 圖片"""
    # 建立簡單的圖片（使用 PIL 或直接用現成圖片）
    # 這裡我們用程式產生一個簡單的圖片

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("請先安裝 Pillow: pip install Pillow")
        return False

    # 建立圖片
    img = Image.new('RGB', (2500, 843), color='#06C755')
    draw = ImageDraw.Draw(img)

    # 畫分隔線
    draw.line([(1250, 0), (1250, 843)], fill='white', width=3)

    # 嘗試載入字體，失敗就用預設
    try:
        # macOS 中文字體
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 72)
        small_font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 48)
    except:
        try:
            # 備用字體
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except:
            font = ImageFont.load_default()
            small_font = font

    # 左邊文字
    draw.text((625, 350), "📊 今日收支", fill='white', font=font, anchor='mm')
    draw.text((625, 450), "查看今天的記帳", fill='#E8F5E9', font=small_font, anchor='mm')

    # 右邊文字
    draw.text((1875, 350), "🌐 網頁版", fill='white', font=font, anchor='mm')
    draw.text((1875, 450), "開啟完整功能", fill='#E8F5E9', font=small_font, anchor='mm')

    # 儲存圖片
    img_path = "rich_menu.png"
    img.save(img_path)
    print(f"圖片已儲存: {img_path}")

    # 上傳圖片
    with open(img_path, 'rb') as f:
        response = httpx.post(
            f"{BASE_URL}/richmenu/{rich_menu_id}/content",
            headers={
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "image/png"
            },
            content=f.read()
        )

    if response.status_code != 200:
        print(f"上傳圖片失敗: {response.text}")
        return False

    print("圖片上傳成功！")
    return True


def set_default_rich_menu(rich_menu_id: str):
    """設為預設 Rich Menu（所有用戶都會看到）"""
    response = httpx.post(
        f"{BASE_URL}/user/all/richmenu/{rich_menu_id}",
        headers=HEADERS
    )

    if response.status_code != 200:
        print(f"設定預設失敗: {response.text}")
        return False

    print("已設為預設 Rich Menu！")
    return True


def delete_all_rich_menus():
    """刪除所有現有的 Rich Menu"""
    response = httpx.get(
        f"{BASE_URL}/richmenu/list",
        headers=HEADERS
    )

    if response.status_code == 200:
        menus = response.json().get("richmenus", [])
        for menu in menus:
            httpx.delete(
                f"{BASE_URL}/richmenu/{menu['richMenuId']}",
                headers=HEADERS
            )
            print(f"已刪除: {menu['richMenuId']}")


def main():
    print("=== LINE Rich Menu 設定工具 ===\n")

    # 1. 刪除舊的 Rich Menu
    print("1. 清除舊的 Rich Menu...")
    delete_all_rich_menus()

    # 2. 建立新的 Rich Menu
    print("\n2. 建立新的 Rich Menu...")
    rich_menu_id = create_rich_menu()
    if not rich_menu_id:
        return

    # 3. 上傳圖片
    print("\n3. 上傳選單圖片...")
    if not upload_rich_menu_image(rich_menu_id):
        return

    # 4. 設為預設
    print("\n4. 設為預設選單...")
    set_default_rich_menu(rich_menu_id)

    print("\n=== 完成！請重新開啟 LINE 聊天室查看 ===")


if __name__ == "__main__":
    main()
