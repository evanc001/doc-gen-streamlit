import json
import streamlit as st
from pathlib import Path

CLIENTS_FILE = Path("timur_clients.json")

def load_clients():
    if CLIENTS_FILE.exists():
        try:
            with open(CLIENTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []

def save_clients(clients):
    try:
        with open(CLIENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(clients, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Ошибка при сохранении списка компаний: {e}")

def edit_clients():
    st.subheader("🧾 Список компаний Тимура")
    clients = load_clients()
    default_text = "\n".join(clients) if clients else ""

    edited_text = st.text_area(
        "Редактируйте список компаний (по одной в строке):",
        value=default_text,
        height=200,
        key="clients_editor"
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("💾 Сохранить изменения"):
            new_list = [c.strip().lower() for c in edited_text.split("\n") if c.strip()]
            save_clients(new_list)
            st.success("✅ Список компаний обновлён!")

    with col2:
        if st.button("🔄 Обновить из файла"):
            st.experimental_rerun()

    return load_clients()