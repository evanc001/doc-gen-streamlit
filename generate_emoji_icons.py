"""
Скрипт для генерации простых иконок вместо emoji.
Создает PNG изображения низкого разрешения для замены emoji в проекте.
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Создаем папку для иконок
os.makedirs("assets/icons/emoji", exist_ok=True)

# Размер иконок (32x32 для низкого разрешения)
SIZE = 32
BG_COLOR = (255, 255, 255, 0)  # Прозрачный фон

# Маппинг emoji на простые символы/текст для иконок
EMOJI_ICONS = {
    "📊": ("CHART", (70, 130, 180)),  # Chart - Steel Blue
    "⚙️": ("⚙", (128, 128, 128)),  # Settings - Gray
    "✅": ("✓", (34, 139, 34)),  # Checkmark - Forest Green
    "❌": ("✗", (220, 20, 60)),  # Cross - Crimson
    "📦": ("📦", (139, 69, 19)),  # Package - Saddle Brown
    "💸": ("$", (50, 205, 50)),  # Money - Lime Green
    "🚫": ("🚫", (255, 0, 0)),  # Prohibited - Red
    "🔄": ("↻", (30, 144, 255)),  # Refresh - Dodger Blue
    "🧾": ("📄", (105, 105, 105)),  # Receipt - Dim Gray
    "💾": ("💾", (0, 100, 200)),  # Save - Blue
    "📝": ("📝", (25, 25, 112)),  # Memo - Midnight Blue
    "📄": ("📄", (70, 130, 180)),  # Document - Steel Blue
    "ℹ️": ("i", (0, 123, 255)),  # Info - Blue
    "📌": ("📍", (255, 0, 0)),  # Pin - Red
    "🚚": ("🚚", (255, 140, 0)),  # Truck - Dark Orange
    "📍": ("📍", (255, 0, 0)),  # Location - Red
    "🛢️": ("🛢", (139, 69, 19)),  # Oil Barrel - Saddle Brown
    "🏠": ("🏠", (160, 82, 45)),  # House - Sienna
    "⬇️": ("↓", (0, 0, 0)),  # Download - Black
    "🚀": ("🚀", (255, 20, 147)),  # Rocket - Deep Pink
    "📁": ("📁", (255, 165, 0)),  # Folder - Orange
    "🛠": ("🔧", (128, 128, 128)),  # Tools - Gray
    "🎯": ("🎯", (255, 0, 0)),  # Target - Red
    "📋": ("📋", (70, 130, 180)),  # Clipboard - Steel Blue
    "⚠️": ("⚠", (255, 165, 0)),  # Warning - Orange
    "📈": ("📈", (50, 205, 50)),  # Chart Up - Lime Green
    "🔒": ("🔒", (128, 128, 128)),  # Lock - Gray
    "🎨": ("🎨", (255, 20, 147)),  # Paintbrush - Deep Pink
    "📱": ("📱", (0, 0, 0)),  # Mobile - Black
    "📞": ("📞", (50, 205, 50)),  # Phone - Lime Green
    "📑": ("📑", (220, 20, 60)),  # PDF - Crimson
    "⏳": ("⏳", (255, 140, 0)),  # Clock - Dark Orange
    "🚨": ("🚨", (255, 0, 0)),  # Alarm - Red
}

def create_icon(emoji, text_symbol, color, filename):
    """Создает простую иконку с текстом/символом"""
    # Создаем изображение с прозрачным фоном
    img = Image.new("RGBA", (SIZE, SIZE), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Пытаемся использовать системный шрифт
    try:
        # Для Windows
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        try:
            # Для Linux/Mac
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            # Fallback на стандартный шрифт
            font = ImageFont.load_default()
    
    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text_symbol, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Центрируем текст
    x = (SIZE - text_width) // 2
    y = (SIZE - text_height) // 2 - 2
    
    # Рисуем текст
    draw.text((x, y), text_symbol, fill=color, font=font)
    
    # Сохраняем
    img.save(filename, "PNG")
    print(f"Created: {filename}")

def main():
    """Генерирует все иконки"""
    for emoji, (symbol, color) in EMOJI_ICONS.items():
        # Создаем имя файла на основе emoji
        emoji_name_map = {
            "📊": "chart",
            "⚙️": "settings",
            "✅": "checkmark",
            "❌": "cross",
            "📦": "package",
            "💸": "money",
            "🚫": "prohibited",
            "🔄": "refresh",
            "🧾": "receipt",
            "💾": "save",
            "📝": "memo",
            "📄": "document",
            "ℹ️": "info",
            "📌": "pin",
            "🚚": "truck",
            "📍": "location",
            "🛢️": "oil_barrel",
            "🏠": "house",
            "⬇️": "download",
            "🚀": "rocket",
            "📁": "folder",
            "🛠": "tools",
            "🎯": "target",
            "📋": "clipboard",
            "⚠️": "warning",
            "📈": "chart_up",
            "🔒": "lock",
            "🎨": "paintbrush",
            "📱": "mobile",
            "📞": "phone",
            "📑": "pdf",
            "⏳": "clock",
            "🚨": "alarm",
        }
        
        filename = f"assets/icons/emoji/{emoji_name_map.get(emoji, 'icon')}.png"
        create_icon(emoji, symbol, color, filename)
    
    print("\nВсе иконки созданы!")

if __name__ == "__main__":
    main()

