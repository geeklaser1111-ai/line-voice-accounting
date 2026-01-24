import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    """解析後的交易資料"""
    type: str  # income / expense
    amount: float
    category: str
    description: str


# 分類關鍵字對照
EXPENSE_KEYWORDS = {
    "餐飲": ["早餐", "午餐", "晚餐", "宵夜", "吃", "喝", "飲料", "咖啡", "茶", "餐", "便當", "外送", "美食"],
    "交通": ["計程車", "uber", "捷運", "公車", "高鐵", "火車", "加油", "停車", "機車", "汽車", "交通"],
    "娛樂": ["電影", "遊戲", "唱歌", "ktv", "旅遊", "玩", "門票", "演唱會"],
    "購物": ["買", "購", "衣服", "褲子", "鞋", "包包", "3c", "電腦", "手機", "網購"],
    "生活": ["水電", "瓦斯", "房租", "電話費", "網路費", "日用品", "衛生紙"],
    "醫療": ["看醫生", "藥", "醫院", "診所", "掛號", "健康"],
}

INCOME_KEYWORDS = {
    "薪水": ["薪水", "薪資", "月薪", "工資"],
    "獎金": ["獎金", "年終", "分紅", "紅包"],
    "投資": ["股票", "股息", "利息", "投資", "基金"],
}

# 中文數字對照
CHINESE_NUMBERS = {
    "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "百": 100, "千": 1000, "萬": 10000,
}


def chinese_to_number(text: str) -> Optional[float]:
    """將中文數字轉換成阿拉伯數字"""
    if not text:
        return None

    # 先嘗試直接轉換阿拉伯數字
    clean_text = text.replace(",", "").replace("，", "")
    try:
        return float(clean_text)
    except ValueError:
        pass

    # 處理中文數字
    result = 0
    temp = 0

    for char in text:
        if char in CHINESE_NUMBERS:
            num = CHINESE_NUMBERS[char]
            if num >= 10:
                if temp == 0:
                    temp = 1
                if num == 10000:
                    result = (result + temp) * num
                    temp = 0
                else:
                    temp *= num
                    result += temp
                    temp = 0
            else:
                temp = temp * 10 + num if temp >= 10 else num
        elif char in "塊元錢块":
            continue

    result += temp
    return result if result > 0 else None


def extract_amount(text: str) -> Optional[float]:
    """從文字中提取金額"""
    # 嘗試匹配阿拉伯數字
    patterns = [
        r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:塊|元|錢|块)?",
        r"(?:花了?|用了?|付了?|收到?)\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                return float(amount_str)
            except ValueError:
                pass

    # 嘗試匹配中文數字
    chinese_pattern = r"([零一二兩三四五六七八九十百千萬]+)\s*(?:塊|元|錢|块)?"
    match = re.search(chinese_pattern, text)
    if match:
        return chinese_to_number(match.group(1))

    return None


def determine_category(text: str) -> tuple[str, str]:
    """判斷分類和類型（收入/支出）"""
    text_lower = text.lower()

    # 先檢查是否為收入
    for category, keywords in INCOME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return "income", category

    # 檢查支出分類
    for category, keywords in EXPENSE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return "expense", category

    # 預設為支出-其他
    return "expense", "其他"


def parse_transaction(text: str) -> Optional[ParsedTransaction]:
    """解析記帳文字"""
    if not text:
        return None

    amount = extract_amount(text)
    if amount is None:
        return None

    trans_type, category = determine_category(text)

    return ParsedTransaction(
        type=trans_type,
        amount=amount,
        category=category,
        description=text
    )
