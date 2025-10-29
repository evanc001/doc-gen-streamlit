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
from typing import Optional

from data_utils import load_sheet_data
from clients_manager import edit_clients


def _select_company_column(df: pd.DataFrame) -> Optional[str]:
    """Возвращает название столбца, содержащего наименование компании.

    В исходных таблицах колонка с клиентом/компанией может называться
    по‑разному (например, «Компания», «Контрагент», «Клиент» или даже
    содержать месяц, если файл некорректно отформатирован). Эта функция
    ищет первое совпадение по ключевым словам, игнорируя регистр и
    лишние пробелы. Если подходящая колонка не найдена, возвращает None.
    """
    keywords = [
        "компания",
        "контрагент",
        "клиент",
        "customer",
        "client",
    ]
    for col in df.columns:
        col_norm = str(col).strip().lower()
        for kw in keywords:
            if kw in col_norm:
                return col
    return None


def display_dashboard() -> None:
    """Отображает пользовательский интерфейс дашборда."""
    st.set_page_config(page_title="Дашборд по продажам", layout="wide")
    st.title("📊 Дашборд по продажам топлива")

    st.sidebar.header("⚙️ Настройки")

    # Блок выбора источника данных
    st.sidebar.subheader("Источник данных")
    sheet_id_default: str = ""
    # Попробуем получить значение по умолчанию из secrets (если
    # пользователь указал ID таблицы в конфигурации).
    try:
        sheet_id_default = str(st.secrets.get("default_sheet_id", ""))
    except Exception:
        sheet_id_default = ""

    sheet_id = st.sidebar.text_input(
        "ID Google Sheets", value=sheet_id_default,
        help=(
            "Укажите идентификатор Google Sheets. Таблица должна быть "
            "доступна либо публично, либо через сервисный аккаунт, "
            "настроенный в секции secrets."
        ),
    )
    uploaded_file = st.sidebar.file_uploader(
        "Или загрузите Excel‑файл", type=["xlsx", "xlsm", "xls"],
    )

    # Список компаний для Тимура
    timur_clients = edit_clients()

    st.markdown("---")
    st.info("Загрузка данных из источника…")

    # Загрузка данных с учётом выбранного источника
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

    # Копируем датафрейм, приводим названия колонок к единому виду
    df = df_month.copy()
    df.columns = df.columns.str.strip()

    company_col = _select_company_column(df)
    if company_col is None:
        st.error(
            "❌ Не удалось определить столбец с названием компании. "
            "Убедитесь, что в таблице есть колонка с названием клиента "
            "(например, 'Компания', 'Контрагент', 'Клиент')."
        )
        return

    # Создаём нормализованную колонку для сопоставления с списком компаний
    df["Компания"] = df[company_col].astype(str).str.strip()
    df["company_key"] = df["Компания"].str.lower()
    df_filtered = df[df["company_key"].isin(timur_clients)]

    # Рассчитываем ключевые показатели
    total_volume = df_filtered.get("Кол-во отгруженного, тн", pd.Series(dtype=float)).sum()
    total_profit = df_filtered.get("Итого заработали", pd.Series(dtype=float)).sum()
    transport_expenses = df_filtered.get("транспорт", pd.Series(dtype=float)).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Всего отгружено, тн",
        f"{total_volume:,.3f}".replace(",", " ") if not pd.isna(total_volume) else "-",
    )
    c2.metric(
        "Всего заработано",
        f"{total_profit:,.0f}".replace(",", " ") if not pd.isna(total_profit) else "-",
    )
    c3.metric(
        "Транспортные расходы",
        f"{transport_expenses:,.0f}".replace(",", " ") if not pd.isna(transport_expenses) else "-",
    )

    st.markdown("---")
    st.subheader("🔢 Последние номера доп. соглашений по компаниям")
    ds_col = "№ доп контрагент"
    if ds_col in df_filtered.columns:
        last_ds = (
            df_filtered.groupby("Компания")[ds_col].max().reset_index().rename(
                columns={ds_col: "Последний № ДС"}
            )
        )
        # Приводим номера к целому типу, если возможно
        last_ds["Последний № ДС"] = last_ds["Последний № ДС"].apply(
            lambda x: int(x) if pd.notna(x) and str(x).isdigit() else np.nan
        )
        last_ds = last_ds.dropna(subset=["Последний № ДС"])
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(last_ds, hide_index=True)
    else:
        st.info("Нет столбца с номерами доп. соглашений.")

    st.subheader("📦 Общие показатели по компаниям")
    cols_needed = {"Компания", "Кол-во отгруженного, тн", "Итого заработали"}
    if cols_needed.issubset(set(df_filtered.columns)):
        total_by_company = (
            df_filtered.groupby("Компания")[
                ["Кол-во отгруженного, тн", "Итого заработали"]
            ]
            .sum()
            .reset_index()
        )
        total_by_company = total_by_company[
            (total_by_company["Кол-во отгруженного, тн"] > 0)
            | (total_by_company["Итого заработали"] > 0)
        ]
        total_by_company["Кол-во отгруженного, тн"] = total_by_company[
            "Кол-во отгруженного, тн"
        ].round(3)
        total_by_company["Итого заработали"] = total_by_company[
            "Итого заработали"
        ].round(0)
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(total_by_company, hide_index=True)
    else:
        st.info(
            "Не найдены все необходимые столбцы для расчёта общих показателей "
            "(требуются 'Кол-во отгруженного, тн' и 'Итого заработали')."
        )

    st.subheader("💸 Должники")
    debt_col = "долг"
    if debt_col in df_filtered.columns:
        debts = df_filtered.groupby("Компания")[debt_col].sum().reset_index()
        debts = debts[debts[debt_col] > 0]
        debts = debts.rename(columns={debt_col: "Сумма долга"})
        st.dataframe(debts, hide_index=True)
    else:
        st.info(
            "Столбец 'долг' отсутствует — таблица должников не сформирована."
        )

    st.markdown("---")
    st.caption("🔄 Данные обновляются напрямую из Google Sheets или загруженного файла.")


if __name__ == "__main__":
    display_dashboard()