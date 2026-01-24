import httpx
from openai import OpenAI
from config import OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN


def download_audio_from_line(message_id: str) -> bytes:
    """從 LINE 下載語音檔案"""
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    with httpx.Client() as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.content


def transcribe_audio(audio_content: bytes) -> str:
    """使用 Whisper API 將語音轉成文字"""
    client = OpenAI(api_key=OPENAI_API_KEY)

    # 將 bytes 寫入臨時檔案
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as temp_file:
        temp_file.write(audio_content)
        temp_path = temp_file.name

    try:
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="zh"
            )
        return transcript.text
    finally:
        os.unlink(temp_path)


def process_voice_message(message_id: str) -> str:
    """處理語音訊息：下載並轉換成文字"""
    audio_content = download_audio_from_line(message_id)
    text = transcribe_audio(audio_content)
    return text
