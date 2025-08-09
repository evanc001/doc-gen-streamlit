"""
Модуль dashboard содержит функции для отображения дашборда
в Streamlit‑приложении. Дашборд показывает сводную статистику
по сделкам за последний месяц, основываясь на данных из Excel‑файла,
полученного из Google Sheets или загруженного вручную.

Функция ``display_dashboard`` выводит интерактивный интерфейс,
позволяющий загрузить файл, выбрать период и увидеть основные
показатели. Структура вынесена в отдельный модуль для лучшей
организации кода.
"""

from __future__ import annotations

import datetime
from typing import Optional

import streamlit as st
import pandas as pd

from data_utils import (
    load_dictionaries,
    load_sheet_data,
    parse_transport_table,
    prepare_dashboard_summary,
)


def _inject_custom_style() -> None:
    """Вставляет пользовательские CSS‑стили для улучшения дизайна.

    Изменяет внешний вид карточек, таблиц и фоновых элементов,
    чтобы придать приложению более современный и лаконичный вид.
    """
    st.markdown(
        """
        <style>
        /* Универсальный фон и шрифты */
        body {
            font-family: "Segoe UI", "Helvetica Neue", sans-serif;
        }
        /* Метрики */
        .stMetric {
            background-color: #f7f7f9;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        /* Заголовки */
        h2, h3, h4 {
            color: #333333;
        }
        /* Таблица */
        .stDataFrame table {
            border-collapse: collapse;
        }
        .stDataFrame th, .stDataFrame td {
            padding: 8px 12px;
            border: 1px solid #e6e6e6;
        }
        /* Красный текст для предупреждений */
        .danger {
            color: #c0392b;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def display_dashboard(sheet_id: Optional[str] = None) -> None:
    """Отображает дашборд на отдельной вкладке Streamlit.

    Args:
        sheet_id: идентификатор Google Sheets. Если передан, приложение
            попробует скачать данные по ссылке. При отсутствии доступа
            необходимо использовать загрузку файла вручную.
    """
    # Настраиваем стиль
    _inject_custom_style()
    # Заголовок
    st.subheader("📊 Дашборд по сделкам (последний месяц)")
    # Предлагаем загрузить файл
    uploaded_file = st.file_uploader(
        "Загрузите свежий Excel‑файл (.xlsx) с данными или оставьте поле пустым для автоматической загрузки", 
        type=["xlsx"],
        help="Вы можете предварительно скачать таблицу из Google Sheets и загрузить её здесь"
    )
    # Кнопка обновления для ручного вызова
    if st.button("🔁 Обновить данные"):
        # Используем состояние сессии для принудительного обновления
        st.session_state['refresh_data'] = True
    # Определяем дату (сегодня) для определения листа
    current_date = datetime.date.today()
    try:
        # Загружаем данные
        df_month, df_raw, sheet_name = load_sheet_data(
            file=uploaded_file,
            sheet_id=sheet_id,
            date=current_date,
            prefer_cache=not st.session_state.get('refresh_data', False)
        )
        # После успешной загрузки снимаем флаг обновления
        st.session_state['refresh_data'] = False
    except Exception as exc:
        st.error(f"❌ Ошибка загрузки данных: {exc}")
        return
    # Получаем словари и парсим транспортную таблицу
    clients_dict, _, _, _ = load_dictionaries()
    transport_map = parse_transport_table(df_raw)
    summary, totals = prepare_dashboard_summary(df_month, clients_dict, transport_map)
    # Выводим метрики
    col1, col2, col3 = st.columns(3)
    col1.metric("Всего отгружено, тн", f"{totals['total_volume']}")
    col2.metric("Всего заработано", f"{totals['total_profit']:.2f}")
    col3.metric("Транспортные расходы", f"{totals['total_transport']:.2f}")
    st.markdown("### 📦 Сводка по компаниям")
    if summary:
        df_summary = pd.DataFrame(summary)
        df_summary['Водитель отсутствует'] = df_summary['Водитель отсутствует'].map({True: 'Да', False: 'Нет'})
        st.dataframe(df_summary, use_container_width=True)
    else:
        st.info("Нет данных для ваших клиентов за выбранный месяц.")