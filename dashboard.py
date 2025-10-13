import streamlit as st
import pandas as pd
import numpy as np
from data_utils import load_sheet_data
from clients_manager import edit_clients

SHEET_ID = "1nyYdsFmSY1hmPdLh4HzgEU5vAgg96NpUjbCg0WRJPfY"

def display_dashboard():
    st.title("📊 Дашборд по продажам топлива")

    st.sidebar.header("⚙️ Настройки")
    timur_clients = edit_clients()

    st.markdown("---")
    st.info("Загрузка данных из Google Sheets...")

    try:
        df_month, df_raw, sheet_name = load_sheet_data(sheet_id=SHEET_ID)
        st.success(f"✅ Загружен лист: {sheet_name}")
    except Exception as e:
        st.error(f"❌ Ошибка загрузки Google Sheets: {e}")
        return

    df = df_month.copy()
    df.columns = df.columns.str.strip()

    if "ОКТЯБРЬ 2025" not in df.columns:
        st.error("❌ В таблице не найден столбец 'Компания'.")
        return

    df["Компания"] = df["ОКТЯБРЬ 2025"].astype(str).str.strip()
    df["company_key"] = df["Компания"].str.lower()
    df_filtered = df[df["company_key"].isin(timur_clients)]

    total_volume = df_filtered.get("Кол-во отгруженного, тн", pd.Series(dtype=float)).sum()
    total_profit = df_filtered.get("Итого заработали", pd.Series(dtype=float)).sum()
    transport_expenses = df_filtered.get("транспорт", pd.Series(dtype=float)).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Всего отгружено, тн", f"{total_volume:,.3f}".replace(",", " "))
    c2.metric("Всего заработано", f"{total_profit:,.0f}".replace(",", " "))
    c3.metric("Транспортные расходы", f"{transport_expenses:,.0f}".replace(",", " "))

    st.markdown("---")

    st.subheader("🔢 Последние номера доп. соглашений по компаниям")
    if "№ доп контрагент" in df_filtered.columns:
        last_ds = (
            df_filtered.groupby("Компания")["№ доп контрагент"]
            .max()
            .reset_index()
            .rename(columns={"№ доп контрагент": "Последний № ДС"})
        )
        last_ds["Последний № ДС"] = last_ds["Последний № ДС"].apply(lambda x: int(x) if pd.notna(x) else np.nan)
        last_ds = last_ds.dropna(subset=["Последний № ДС"])
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(last_ds, hide_index=True)
    else:
        st.warning("Нет столбца '№ доп контрагент'.")

    st.subheader("📦 Общие показатели по компаниям")
    if {"Компания", "Кол-во отгруженного, тн", "Итого заработали"} <= set(df_filtered.columns):
        total_by_company = (
            df_filtered.groupby("Компания")[["Кол-во отгруженного, тн", "Итого заработали"]]
            .sum()
            .reset_index()
        )
        total_by_company = total_by_company[(total_by_company["Кол-во отгруженного, тн"] > 0) |
                                            (total_by_company["Итого заработали"] > 0)]
        total_by_company["Кол-во отгруженного, тн"] = total_by_company["Кол-во отгруженного, тн"].round(3)
        total_by_company["Итого заработали"] = total_by_company["Итого заработали"].round(0)
        with st.expander("Показать / скрыть таблицу"):
            st.dataframe(total_by_company, hide_index=True)
    else:
        st.warning("Не найдены столбцы для расчёта общих показателей.")

    st.subheader("💸 Должники")
    if "долг" in df_filtered.columns:
        debts = df_filtered.groupby("Компания")["долг"].sum().reset_index()
        debts = debts[debts["долг"] > 0]
        debts = debts.rename(columns={"долг": "Сумма долга"})
        st.dataframe(debts, hide_index=True)
    else:
        st.info("Столбец 'долг' отсутствует — таблица должников не сформирована.")

    st.markdown("---")
    st.caption("🔄 Данные обновляются напрямую из Google Sheets.")


if __name__ == "__main__":
    display_dashboard()
