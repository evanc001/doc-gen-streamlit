"""Тестовый скрипт для проверки работы иконок."""
from emoji_icons import get_icon_html

# Тестируем несколько иконок
test_emojis = ["📊", "✅", "📦", "🔄"]

print("Тестирование иконок:")
for emoji in test_emojis:
    html = get_icon_html(emoji, 24)
    if "data:image" in html:
        print(f"✅ {emoji} - OK (base64 encoded)")
    elif emoji in html:
        print(f"⚠️  {emoji} - Fallback на emoji (файл не найден)")
    else:
        print(f"❌ {emoji} - Ошибка")

