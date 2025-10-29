"""
Основной модуль Streamlit‑приложения.

Этот файл реализует дашборд по продажам топлива. Пользователь может
выбрать источник данных — либо указать идентификатор Google Sheets
таблицы, либо загрузить локальный Excel‑файл. Для чтения приватных
таблиц используется функция ``load_sheet_data`` из ``data_utils``,
которая поддерживает аутентификацию через сервисный аккаунт Google.

Также реализован интерфейс для редактирования списка компаний,
закреплённых за Тимуром. Этот список хранится локально в файле
``timur_clients.json`` и управляется функцией ``edit_clients``
из модуля ``clients_manager``.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

from data_utils import load_sheet_data, parse_company_and_transport, aggregate_company_metrics
from clients_manager import edit_clients


# Карта синонимов для сокращённых названий компаний.
# При необходимости расширяйте этот словарь: ключ — вариант в нижнем
# регистре, значение — каноническое название. Например,
# "м7" и "м7 soft" -> "м7 софт".
SYNONYMS: Dict[str, str] = {
    'м7': 'м7 софт',
    'm7': 'м7 софт',
    'm7 soft': 'м7 софт',
    'м7 soft': 'м7 софт',
    'тритон': 'тритон трейд',
    'triton': 'тритон трейд',
    'тритон трейд': 'тритон трейд',
    'тритион': 'тритон трейд',
    'транзитсити': 'тк транзит сити',
    'трк транзит сити': 'тк транзит сити',
    'транзит сити': 'тк транзит сити',
    # Добавляйте другие варианты при необходимости
}


def display_dashboard() -> None:
    """Отображает пользовательский интерфейс дашборда."""
    st.set_page_config(page_title="Дашборд по продажам", layout="wide")
    st.title("📊 Дашборд по продажам топлива")

    # Блок настроек: теперь размещаем поля в основном интерфейсе, чтобы они
    # были видимы даже при свернутой боковой панели. Можно использовать
    # columns для компактного размещения.
    st.markdown("### ⚙️ Настройки")
    try:
        sheet_id_default = str(st.secrets.get("default_sheet_id", ""))
    except Exception:
        sheet_id_default = ""
    col_setting1, col_setting2 = st.columns(2)
    with col_setting1:
        sheet_id = st.text_input(
            "ID Google Sheets",
            value=sheet_id_default,
            help=(
                "Укажите идентификатор Google Sheets. Таблица должна быть доступна "
                "либо публично, либо через сервисный аккаунт, указанный в .streamlit/secrets.toml."
            ),
        )
    with col_setting2:
        uploaded_file = st.file_uploader(
            "Или загрузите Excel‑файл", type=["xlsx", "xlsm", "xls"],
        )
    filter_option = st.radio("Фильтр компаний", options=["Тимур", "Все"], index=0)
    timur_clients = edit_clients()

    st.markdown("---")
    st.info("Загрузка данных из источника…")
    # Загрузка данных
    try:
        if uploaded_file is not None:
            df_month, df_raw, sheet_name = load_sheet_data(file=uploaded_file)
        elif sheet_id:
            df_month, df_raw, sheet_name = load_sheet_data(sheet_id=sheet_id)
        else:
            st.warning("Пожалуйста, введите ID Google Sheets или загрузите файл.")
            return
        st.success(f"✅ Загружен лист: {sheet_name}")
    except Exception as e:
        st.error(f"❌ Ошибка загрузки данных: {e}")
        return
    # Парсим таблицы продаж и транспортных услуг
    try:
        sales_df, transport_df = parse_company_and_transport(df_raw)
    except Exception as e:
        st.error(f"Ошибка при разборе таблицы: {e}")
        return
    # Определяем список компаний для фильтрации
    if filter_option == "Тимур":
        company_filter = timur_clients
    else:
        company_filter = None
    # Агрегируем данные
    agg_results = aggregate_company_metrics(
        sales_df,
        transport_df,
        company_filter=company_filter,
        synonyms=SYNONYMS,
    )
    summary_df: pd.DataFrame = agg_results['summary']
    debt_table: pd.DataFrame = agg_results['debt_table']
    attention_df: pd.DataFrame = agg_results['attention']
    missing_driver_df: pd.DataFrame = agg_results['missing_driver']
    # Основные метрики (чистая прибыль, транспортные расходы, прибыль)
    total_net_profit = summary_df['net_profit'].sum()
    total_transport = summary_df['transport_cost'].sum()
    total_profit = summary_df['profit'].sum()
    total_tonnage = summary_df['tonnage'].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Общий тоннаж, тн", f"{total_tonnage:,.2f}".replace(",", " "))
    c2.metric("Общая прибыль", f"{total_profit:,.0f}".replace(",", " "))
    c3.metric("Транспортные расходы", f"{total_transport:,.0f}".replace(",", " "))
    c4.metric("Чистая прибыль", f"{total_net_profit:,.0f}".replace(",", " "))

    st.markdown("---")
    st.subheader("📦 Сводные показатели по компаниям")
    if not summary_df.empty:
        # Переименовываем для отображения
        display_df = summary_df.rename(columns={
            'company': 'Компания',
            'tonnage': 'Тоннаж (тн)',
            'profit': 'Прибыль',
            'transport_cost': 'Транспорт',
            'net_profit': 'Чистая прибыль'
        })
        display_df = display_df.sort_values('Чистая прибыль', ascending=False)
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(display_df, hide_index=True)
    else:
        st.info("Нет данных для выбранного фильтра.")

    st.subheader("💸 Задолженность / Переплата")
    if not debt_table.empty:
        debt_df = debt_table.copy()
        debt_df = debt_df.rename(columns={'company': 'Компания', 'debt': 'Сумма'})
        # Визуально выделяем задолженность (положительная) и переплату (отрицательная)
        def color_debt(val: float) -> str:
            if val > 0:
                return 'background-color: rgba(255, 0, 0, 0.2)'
            elif val < 0:
                return 'background-color: rgba(0, 128, 0, 0.2)'
            else:
                return ''
        styled = debt_df.style.applymap(color_debt, subset=['Сумма']).format({
            'Сумма': '{:,.0f}'.format
        })
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(styled, hide_index=True)
    else:
        st.info("Нет информации о задолженности или переплате.")

    st.subheader("🚩 Строки, требующие внимания (тоннаж ≤ 0)")
    if not attention_df.empty:
        att_df = attention_df[['company', 'tonnage', 'profit', 'row_number']].rename(columns={
            'company': 'Компания',
            'tonnage': 'Тоннаж',
            'profit': 'Прибыль',
            'row_number': 'Номер строки'
        })
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(att_df, hide_index=True)
    else:
        st.info("Нет строк, где тоннаж пустой или отрицательный.")

    st.subheader("🚫 Строки без указания водителя")
    if not missing_driver_df.empty:
        miss_df = missing_driver_df[['company', 'tonnage', 'profit', 'row_number']].rename(columns={
            'company': 'Компания',
            'tonnage': 'Тоннаж',
            'profit': 'Прибыль',
            'row_number': 'Номер строки'
        })
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(miss_df, hide_index=True)
    else:
        st.info("Все строки содержат информацию о водителе.")

    st.markdown("---")
    st.caption("🔄 Данные обновляются напрямую из Google Sheets или загруженного файла.")


if __name__ == "__main__":
    display_dashboard()