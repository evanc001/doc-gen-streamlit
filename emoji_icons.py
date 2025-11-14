"""
Вспомогательный модуль для работы с иконками вместо emoji.
"""

from pathlib import Path

# Базовый путь к иконкам
ICONS_BASE_PATH = Path("assets/icons/emoji")

# Маппинг emoji на имена файлов иконок
EMOJI_TO_ICON = {
    "📊": "chart.svg",
    "⚙️": "settings.svg",
    "✅": "checkmark.svg",
    "❌": "cross.svg",
    "📦": "package.svg",
    "💸": "money.svg",
    "🚫": "prohibited.svg",
    "🔄": "refresh.svg",
    "🧾": "receipt.svg",
    "💾": "save.svg",
    "📝": "memo.svg",
    "📄": "document.svg",
    "ℹ️": "info.svg",
    "📌": "pin.svg",
    "🚚": "truck.svg",
    "📍": "location.svg",
    "🛢️": "oil_barrel.svg",
    "🏠": "house.svg",
    "⬇️": "download.svg",
    "🚀": "rocket.svg",
    "📁": "folder.svg",
    "🛠": "tools.svg",
    "🎯": "target.svg",
    "📋": "clipboard.svg",
    "⚠️": "warning.svg",
    "📈": "chart_up.svg",
    "🔒": "lock.svg",
    "🎨": "paintbrush.svg",
    "📱": "mobile.svg",
    "📞": "phone.svg",
    "📑": "pdf.svg",
    "⏳": "clock.svg",
    "🚨": "alarm.svg",
}

def get_icon_path(emoji: str) -> str:
    """Возвращает путь к иконке для данного emoji."""
    icon_file = EMOJI_TO_ICON.get(emoji)
    if icon_file:
        return str(ICONS_BASE_PATH / icon_file)
    return None

def get_icon_html(emoji: str, size: int = 16, alt: str = None) -> str:
    """Возвращает HTML тег <img> для emoji."""
    icon_path = get_icon_path(emoji)
    if not icon_path:
        return emoji  # Fallback на emoji, если иконка не найдена
    
    if alt is None:
        alt = f"emoji: {emoji}"
    
    return f'<img src="{icon_path}" alt="{alt}" width="{size}" height="{size}" style="vertical-align: middle; display: inline-block;">'

def get_icon_markdown(emoji: str, alt: str = None) -> str:
    """Возвращает Markdown изображение для emoji."""
    icon_path = get_icon_path(emoji)
    if not icon_path:
        return emoji  # Fallback на emoji, если иконка не найдена
    
    if alt is None:
        alt = f"emoji: {emoji}"
    
    return f'![{alt}]({icon_path})'

