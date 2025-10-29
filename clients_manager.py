"""
Управление списком компаний, закреплённых за Тимуром.

Функции в этом модуле позволяют загрузить список клиентов из файла,
дать пользователю возможность отредактировать этот список через
Streamlit, и сохранить результат обратно в JSON. Список хранится в
файле ``timur_clients.json`` в корневой директории приложения.
"""

import json
import streamlit as st
from pathlib import Path
from typing import List

# Путь к файлу, где хранится список клиентов. Используем относительный
# путь, чтобы файл лежал рядом с запуском приложения.
CLIENTS_FILE = Path("timur_clients.json")


def load_clients() -> List[str]:
    """Загружает список компаний из файла JSON.

    Returns:
        List[str]: список названий компаний в нижнем регистре.
    """
    if CLIENTS_FILE.exists():
        try:
            with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save_clients(clients: List[str]) -> None:
    """Сохраняет список компаний в JSON‑файл.

    Args:
        clients: список компаний в нижнем регистре.
    """
    try:
        with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(clients, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Ошибка при сохранении списка компаний: {e}")


def edit_clients() -> List[str]:
    """Интерфейс Streamlit для редактирования списка клиентов.

    Позволяет пользователю добавлять и удалять названия компаний,
    закреплённых за Тимуром. Возвращает обновлённый список для
    дальнейшего использования в фильтрации данных.

    Returns:
        List[str]: список названий компаний в нижнем регистре.
    """
    st.subheader("🧾 Список компаний Тимура")
    clients = load_clients()
    default_text = "\n".join(clients) if clients else ""

    edited_text = st.text_area(
        "Редактируйте список компаний (по одной в строке):",
        value=default_text,
        height=200,
        key="clients_editor",
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("💾 Сохранить изменения"):
            new_list = [c.strip().lower() for c in edited_text.split("\n") if c.strip()]
            save_clients(new_list)
            st.success("✅ Список компаний обновлён!")

    with col2:
        if st.button("🔄 Обновить из файла"):
            # Обновляем содержимое текстового поля без перезапуска приложения
            refreshed = load_clients()
            updated_text = "\n".join(refreshed) if refreshed else ""
            # Используем session_state, чтобы обновить значение text_area
            st.session_state["clients_editor"] = updated_text
            st.success("✅ Список компаний загружен из файла")

    return load_clients()