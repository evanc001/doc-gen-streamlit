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
    _download_google_sheet,
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
        # Загружаем ExcelFile для получения списка листов
        if uploaded_file is not None:
            excel_file = pd.ExcelFile(uploaded_file)
        elif sheet_id:
            excel_file = _download_google_sheet(sheet_id)
        else:
            raise RuntimeError("Не указан источник данных")
    except Exception as exc:
        st.error(f"❌ Ошибка загрузки файла: {exc}")
        return
    # Предлагаем выбрать лист (месяц)
    sheet_names = excel_file.sheet_names
    # Сортируем листы так, чтобы последние месяцы были первыми
    sheet_names_sorted = sorted(sheet_names, key=lambda x: (x.split()[-1], x.split()[0]), reverse=True)
    default_sheet = sheet_names_sorted[0]
    selected_sheet = st.selectbox(
        "Выберите месяц (лист)",
        options=sheet_names_sorted,
        index=0,
        help="Выберите лист из файла для анализа."
    )
    # Читаем данные выбранного листа
    try:
        df_month = pd.read_excel(excel_file, sheet_name=selected_sheet, header=2)
        df_raw = pd.read_excel(excel_file, sheet_name=selected_sheet, header=None)
    except Exception as exc:
        st.error(f"❌ Ошибка чтения листа '{selected_sheet}': {exc}")
        return
    # Получаем словари клиентов и транспортную таблицу
    clients_dict, _, _, _ = load_dictionaries()
    transport_map = parse_transport_table(df_raw)
    # Фильтруем сделки: учитываем только строки, где указан номер ДС
    df_month = df_month.copy()
    # Нормализуем названия компаний и номер ДС
    df_month['company_key'] = df_month['Компания'].astype(str).str.lower().str.strip()
    # Номера дополнительных соглашений для покупателя и поставщика
    df_month['ds_client'] = pd.to_numeric(df_month['№ доп контрагент'], errors='coerce')
    df_month['ds_supplier'] = pd.to_numeric(df_month.get('№ доп поставщик'), errors='coerce')
    # Конвертируем числовые колонки в тип float для корректного суммирования
    df_month['volume'] = pd.to_numeric(df_month['кол-во отгруженного, тн'], errors='coerce')
    df_month['profit'] = pd.to_numeric(df_month['Итого заработали'], errors='coerce')
    # Сделки считаем только для строк, где нет номера ДС поставщика (то есть это сделки контрагента)
    df_deals = df_month[df_month['ds_supplier'].isna()]
    # Исключаем строки, где название компании отсутствует или представляет собой число (это заголовки/промежуточные строки)
    df_deals = df_deals[df_deals['company_key'].notna()]
    df_deals = df_deals[~df_deals['company_key'].str.fullmatch(r'\d+(\.\d+)?', na=False)]
    # Даем возможность пользователю выбрать компании для анализа
    available_companies = sorted(df_deals['company_key'].unique())
    # Создаем список клиентов по умолчанию, используя clients_dict и синонимы
    default_selected: list[str] = []
    # Поддержка синонимов: если в clients_dict есть сокращённое название, ищем полное в available_companies
    synonyms_map = {
        'тритон': 'тритон трейд',
        'транзитсити': 'тк транзит сити',
        'кайрос': 'кайрос тк',
        'м7': 'м7 софт',
    }
    client_keys = set(clients_dict.keys())
    for comp in available_companies:
        # Сначала проверяем прямое совпадение со словарем клиентов
        if comp in client_keys:
            default_selected.append(comp)
        else:
            # Если в clients_dict сокращенное название клиента присутствует в синонимах, включаем полное
            for short_name, full_name in synonyms_map.items():
                if short_name in client_keys and full_name.lower() == comp:
                    default_selected.append(comp)
                    break
    # Если ни одной компании не совпало с клиентами, по умолчанию выбираем все
    if not default_selected:
        default_selected = available_companies.copy()
    # Фильтр: Тимур = клиенты из json и синонимы, Все = все компании
    filter_mode = st.radio(
        "Фильтр компаний", options=["Тимур", "Все"], index=0,
        help="Выберите 'Тимур', чтобы отображать компании из вашего списка, или 'Все' — все компании из таблицы."
    )
    if filter_mode == "Тимур":
        selected_companies = default_selected
    else:
        selected_companies = available_companies
    # Применяем фильтр по выбранным компаниям
    if selected_companies:
        df_deals = df_deals[df_deals['company_key'].isin([c.lower() for c in selected_companies])]
    if df_deals.empty:
        st.info("Нет данных для ваших клиентов за выбранный месяц.")
        return
    # Списки для различных сводок
    last_ds_records: list[dict[str, object]] = []
    volume_profit_records: list[dict[str, object]] = []
    delay_records: list[dict[str, object]] = []
    missing_driver_records: list[dict[str, object]] = []
    total_volume: float = 0.0
    total_profit: float = 0.0
    # Собираем фамилии водителей для подсчёта общих транспортных расходов
    surnames_in_deals = set()
    for _, row in df_deals.iterrows():
        drv_info = row.get('Данные водителя, а/м, п/п и контактные сведения')
        if isinstance(drv_info, str) and drv_info.strip():
            surnames_in_deals.add(drv_info.strip().split()[0].lower())
    # Подсчитываем транспорт по всем сделкам
    transport_total = sum(transport_map.get(s, 0.0) for s in surnames_in_deals)
    # Группируем данные по компаниям
    for comp_key in sorted(df_deals['company_key'].unique()):
        comp_df = df_deals[df_deals['company_key'] == comp_key]
        # Последний номер ДС (максимальный среди указанных для контрагента)
        ds_series = comp_df['ds_client'].dropna()
        try:
            last_ds = int(ds_series.max()) if not ds_series.empty else None
        except Exception:
            last_ds = None
        # Исключаем строки без цены: если нет значения ни в поставщике, ни в контрагенте, пропускаем такие строки во всех метриках
        price_supplier_col = 'цена за 1 т поставщика' if 'цена за 1 т поставщика' in comp_df.columns else None
        price_client_col = 'цена за 1 т контрагенту с доп. услугами' if 'цена за 1 т контрагенту с доп. услугами' in comp_df.columns else None
        if price_supplier_col and price_client_col:
            comp_df_valid = comp_df[~(comp_df[price_supplier_col].isna() & comp_df[price_client_col].isna())]
        else:
            comp_df_valid = comp_df
        # Суммируем объём и прибыль
        vol_sum = comp_df_valid['volume'].fillna(0).sum()
        prof_sum = comp_df_valid['profit'].fillna(0).sum()
        total_volume += vol_sum
        total_profit += prof_sum
        # Сохраняем последний ДС
        last_ds_records.append({'Компания': comp_key, 'Последний № ДС': last_ds})
        volume_profit_records.append({
            'Компания': comp_key,
            'Всего отгружено, тн': vol_sum,
            'Всего заработано': prof_sum
        })
        # Отсрочки: учитываем только строки, которые прошли фильтр comp_df_valid
        pending_df = comp_df_valid[(comp_df_valid['отсрочка платежа, дн'].fillna(0) >= 1) & (comp_df_valid['Оплачено контрагентом'].isna())]
        for _, drow in pending_df.iterrows():
            try:
                delay_days = int(drow['отсрочка платежа, дн'])
            except Exception:
                delay_days = None
            delay_records.append({
                'Компания': comp_key,
                '№ ДС': int(drow['ds_client']) if pd.notna(drow['ds_client']) else None,
                'Отсрочка, дн': delay_days
            })
        # Отсутствие водителя: также игнорируем строки без цены
        for _, drow in comp_df_valid.iterrows():
            drv = drow.get('Данные водителя, а/м, п/п и контактные сведения')
            if not isinstance(drv, str) or not drv.strip():
                missing_driver_records.append({
                    'Компания': comp_key,
                    '№ ДС': int(drow['ds_client']) if pd.notna(drow['ds_client']) else None
                })
    # Вывод метрик
    col1, col2, col3 = st.columns(3)
    col1.metric("Всего отгружено, тн", f"{round(total_volume, 3)}")
    col2.metric("Всего заработано", f"{round(total_profit, 2):.2f}")
    col3.metric("Транспортные расходы", f"{round(transport_total, 2):.2f}")
    # Таблица последних ДС
    st.markdown("#### 🔢 Последние номера доп. соглашений по компаниям")
    df_last_ds = pd.DataFrame(last_ds_records).sort_values(by='Компания').reset_index(drop=True)
    st.table(df_last_ds)
    # Таблица суммарных объёмов и прибыли
    st.markdown("#### 📦 Общие показатели по компаниям")
    df_vol_prof = pd.DataFrame(volume_profit_records).sort_values(by='Всего отгружено, тн', ascending=False).reset_index(drop=True)
    # Форматируем объём и прибыль: объём — 3 знака после запятой, прибыль — без дробной части
    df_vol_prof_display = df_vol_prof.copy()
    df_vol_prof_display['Всего отгружено, тн'] = df_vol_prof_display['Всего отгружено, тн'].apply(lambda x: f"{x:,.3f}".replace(',', ' ').replace('.', ','))
    df_vol_prof_display['Всего заработано'] = df_vol_prof_display['Всего заработано'].apply(lambda x: f"{int(round(x)):,}".replace(',', ' '))
    st.table(df_vol_prof_display)
    # Таблица отсрочек
    if delay_records:
        st.markdown("#### ⏳ Сделки с отсрочкой платежа (не оплачено)")
        df_delay = pd.DataFrame(delay_records)
        st.table(df_delay)
    # Таблица отсутствующих водителей
    if missing_driver_records:
        st.markdown("#### 🚨 Сделки без указания водителя")
        df_missing = pd.DataFrame(missing_driver_records)
        # Выделяем красным цветом
        df_missing_display = df_missing.copy()
        df_missing_display['Компания'] = df_missing_display['Компания'].apply(lambda x: f"<span style='color:#c0392b;'>{x}</span>")
        df_missing_display['№ ДС'] = df_missing_display['№ ДС'].apply(lambda x: f"<span style='color:#c0392b;'>{x}</span>")
        st.markdown(df_missing_display.to_html(escape=False, index=False), unsafe_allow_html=True)