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
    # Получаем словари клиентов и транспортную таблицу
    clients_dict, _, _, _ = load_dictionaries()
    transport_map = parse_transport_table(df_raw)
    # Фильтруем сделки: учитываем только строки, где указан номер ДС
    df_month = df_month.copy()
    # Нормализуем и фильтруем компании
    df_month['company_key'] = df_month['Компания'].astype(str).str.lower().str.strip()
    df_month['ds_num'] = pd.to_numeric(df_month['№ доп контрагент'], errors='coerce')
    df_deals = df_month[df_month['ds_num'].notna()]  # только сделки, где есть номер ДС
    df_deals = df_deals[df_deals['company_key'].isin(clients_dict.keys())]
    if df_deals.empty:
        st.info("Нет данных для ваших клиентов за выбранный месяц.")
        return
    # Списки и словари для различных сводок
    last_ds_records = []  # список {'Компания', 'Последний № ДС'}
    volume_profit_records = []  # список {'Компания', 'Всего отгружено, тн', 'Всего заработано'}
    delay_records = []  # список {'Компания', '№ ДС', 'Отсрочка, дн'}
    missing_driver_records = []  # список {'Компания', '№ ДС', 'Количество, тн', 'Заработано'}
    total_volume = 0.0
    total_profit = 0.0
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
        # Последний номер ДС
        try:
            last_ds = int(comp_df['ds_num'].max())
        except Exception:
            last_ds = None
        vol_sum = comp_df['кол-во отгруженного, тн'].fillna(0).sum()
        prof_sum = comp_df['Итого заработали'].fillna(0).sum()
        total_volume += vol_sum
        total_profit += prof_sum
        last_ds_records.append({'Компания': comp_key, 'Последний № ДС': last_ds})
        volume_profit_records.append({
            'Компания': comp_key,
            'Всего отгружено, тн': round(vol_sum, 3),
            'Всего заработано': round(prof_sum, 2)
        })
        # Отсрочки
        pending_df = comp_df[(comp_df['отсрочка платежа, дн'].fillna(0) >= 1) & (comp_df['Оплачено контрагентом'].isna())]
        for _, drow in pending_df.iterrows():
            try:
                delay_days = int(drow['отсрочка платежа, дн'])
            except Exception:
                delay_days = None
            delay_records.append({
                'Компания': comp_key,
                '№ ДС': int(drow['ds_num']) if pd.notna(drow['ds_num']) else None,
                'Отсрочка, дн': delay_days
            })
        # Отсутствие водителя
        for _, drow in comp_df.iterrows():
            drv = drow.get('Данные водителя, а/м, п/п и контактные сведения')
            if not isinstance(drv, str) or not drv.strip():
                missing_driver_records.append({
                    'Компания': comp_key,
                    '№ ДС': int(drow['ds_num']) if pd.notna(drow['ds_num']) else None,
                    'Количество, тн': round(float(drow['кол-во отгруженного, тн']) if pd.notna(drow['кол-во отгруженного, тн']) else 0.0, 3),
                    'Заработано': round(float(drow['Итого заработали']) if pd.notna(drow['Итого заработали']) else 0.0, 2)
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
    st.table(df_vol_prof)
    # Таблица отсрочек
    if delay_records:
        st.markdown("#### ⏳ Сделки с отсрочкой платежа (не оплачено)")
        df_delay = pd.DataFrame(delay_records)
        st.table(df_delay)
    # Таблица отсутствующих водителей
    if missing_driver_records:
        st.markdown("#### 🚨 Сделки без указания водителя")
        df_missing = pd.DataFrame(missing_driver_records)
        # Покрасим строки, где отсутствует водитель, красным цветом
        df_missing_display = df_missing.copy()
        # Добавляем HTML для выделения цифр
        def _style_driver(val):
            return f"<span style='color:#c0392b;font-weight:bold;'>{val}</span>"
        df_missing_display['Компания'] = df_missing_display['Компания'].apply(lambda x: f"<span style='color:#c0392b;'>{x}</span>")
        df_missing_display['№ ДС'] = df_missing_display['№ ДС'].apply(lambda x: f"<span style='color:#c0392b;'>{x}</span>")
        df_missing_display['Количество, тн'] = df_missing_display['Количество, тн'].apply(lambda x: f"<span style='color:#c0392b;'>{x}</span>")
        df_missing_display['Заработано'] = df_missing_display['Заработано'].apply(lambda x: f"<span style='color:#c0392b;'>{x}</span>")
        st.markdown(df_missing_display.to_html(escape=False, index=False), unsafe_allow_html=True)