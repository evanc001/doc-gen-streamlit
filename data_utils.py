"""
Модуль data_utils предоставляет функции для загрузки и обработки
данных, используемых в приложении. Здесь реализованы операции
чтения JSON словарей, загрузки Excel‑таблиц (как по ссылке, так
и из загруженного файла), парсинг блока «ТРАНСПОРТ +» и
подготовка сводной информации для дашборда.

Добавлена поддержка чтения приватных Google Sheets при помощи
сервисного аккаунта. Если таблицу невозможно скачать напрямую
через `requests` (например, у неё доступ ограничен), функция
``load_sheet_data`` попытается обратиться к Google Sheets API
через библиотеку gspread и учётные данные сервисного аккаунта,
хранящиеся в ``st.secrets["gcp_service_account"]``. При
отсутствии этих зависимостей будет выброшено понятное
исключение.

Функции вынесены из основного файла приложения для удобства
тестирования и облегчения чтения кода.
"""

from __future__ import annotations

import io
import os
import json
import datetime as _dt
from functools import lru_cache
from typing import Dict, Tuple, Iterable, Optional, Any

import pandas as pd
import requests

# Импортируем streamlit и библиотеки для работы с Google API. Эти импорты
# обёрнуты в блок try/except, чтобы модуль мог использоваться вне
# Streamlit без зависимости от gspread. Когда приложение запускается в
# среде Streamlit, реальные модули будут доступны и fallback не
# сработает.
try:
    import streamlit as st  # type: ignore
except Exception:
    # Определяем упрощённый объект с минимально необходимым API,
    # чтобы избежать ошибок при обращении к st.secrets вне Streamlit.
    class _DummyStreamlit:
        def __getattr__(self, item):  # pragma: no cover
            raise AttributeError("streamlit is not installed; install streamlit to use this feature")
    st = _DummyStreamlit()  # type: ignore

try:
    import gspread  # type: ignore
    from google.oauth2.service_account import Credentials  # type: ignore
except Exception:
    # Если библиотек нет, gspread и Credentials будут None; это
    # позволит понять, что подключение к приватным таблицам невозможно.
    gspread = None  # type: ignore
    Credentials = None  # type: ignore


def load_json_dict(filename: str) -> dict:
    """Загружает словарь из JSON‑файла.

    При ошибке чтения или разборе возвращает пустой словарь.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def load_dictionaries(base_dir: Optional[str] = None) -> Tuple[dict, dict, dict, dict]:
    """Загружает словари клиентов, товаров, адресов и нефтебаз.

    Все словари хранятся в подкаталоге ``json`` относительно ``base_dir``.
    Если ``base_dir`` не указана, используется директория текущего файла.

    Returns:
        tuple(dict, dict, dict, dict): клиенты, продукты, локации, нефтебазы
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(base_dir, 'json')
    clients = load_json_dict(os.path.join(json_dir, 'clients.json'))
    products = load_json_dict(os.path.join(json_dir, 'products.json'))
    locations = load_json_dict(os.path.join(json_dir, 'locations.json'))
    neftebazy = load_json_dict(os.path.join(json_dir, 'nb.json'))
    return clients, products, locations, neftebazy


def get_month_sheet_name(month: int, year: int) -> str:
    """Возвращает название листа Google Sheets в формате ``МЕСЯЦ ГОД``.

    Использует русские названия месяцев заглавными буквами.
    """
    months = {
        1: 'ЯНВАРЬ', 2: 'ФЕВРАЛЬ', 3: 'МАРТ', 4: 'АПРЕЛЬ', 5: 'МАЙ', 6: 'ИЮНЬ',
        7: 'ИЮЛЬ', 8: 'АВГУСТ', 9: 'СЕНТЯБРЬ', 10: 'ОКТЯБРЬ', 11: 'НОЯБРЬ', 12: 'ДЕКАБРЬ'
    }
    return f"{months.get(month, '')} {year}"


@lru_cache(maxsize=2)
def _download_google_sheet(sheet_id: str) -> pd.ExcelFile:
    """Внутренняя функция: скачивает Google Sheets как Excel.

    Используется кеширование, чтобы не загружать файл многократно.
    При неудаче выбрасывает исключение.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return pd.ExcelFile(io.BytesIO(resp.content))


def load_sheet_data(
    *,
    file: Optional[Any] = None,
    sheet_id: Optional[str] = None,
    date: Optional[_dt.date] = None,
    prefer_cache: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Загружает данные за месяц из Excel‑таблицы.

    Выбирает лист по текущей или указанной дате (формат «АВГУСТ 2025»).
    Можно передать либо файл (Streamlit uploader), либо идентификатор Google Sheets.

    Args:
        file: файл‑объект Excel (например, из ``st.file_uploader``). Если указан, используется он.
        sheet_id: идентификатор Google Sheets. Если ``file`` не указан, будет предпринята попытка
            скачать файл по ссылке ``export?format=xlsx``.
        date: дата, для которой нужно выбрать лист. По умолчанию используется ``date.today()``.
        prefer_cache: если ``True``, будет использовано кэшированное значение для Google Sheets.

    Returns:
        tuple(pd.DataFrame, pd.DataFrame, str): датафрейм с заголовками (начиная с 3‑ей строки),
            датафрейм «сырой» (без заголовков) и название листа.

    Raises:
        RuntimeError: если не удаётся загрузить файл или найти лист.
    """
    if date is None:
        date = _dt.date.today()
    sheet_name = get_month_sheet_name(date.month, date.year)
    excel_file: Optional[pd.ExcelFile] = None
    # Определяем источник данных
    if file is not None:
        # Загруженный файл может быть либо ``UploadedFile`` от Streamlit, либо bytes
        try:
            excel_file = pd.ExcelFile(file)
        except Exception as exc:
            raise RuntimeError(f"Ошибка чтения загруженного файла: {exc}")
    elif sheet_id:
        # Пытаемся скачать Google Sheets как Excel. Если таблица приватна, то
        # прямой доступ может завершиться ошибкой.
        excel_file = None  # type: Optional[pd.ExcelFile]
        download_exc: Optional[Exception] = None
        try:
            if prefer_cache:
                excel_file = _download_google_sheet(sheet_id)
            else:
                url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                excel_file = pd.ExcelFile(io.BytesIO(resp.content))
        except Exception as exc:
            # Перехватываем исключение, но не выходим сразу — возможно
            # получится загрузить таблицу другим способом.
            download_exc = exc
            excel_file = None
        # Если Excel не загрузился, пробуем локальный файл
        if excel_file is None:
            local_path = f"{sheet_id}.xlsx"
            if os.path.exists(local_path):
                try:
                    excel_file = pd.ExcelFile(local_path)
                except Exception:
                    excel_file = None
        # Если локального файла нет или он не читается, пробуем загрузить
        # приватную таблицу через сервисный аккаунт, если библиотеки доступны
        if excel_file is None and gspread is not None and Credentials is not None:
            # Загружаем сервисные учётные данные из secrets (если они есть)
            creds_info = None
            try:
                if hasattr(st, "secrets"):
                    creds_info = st.secrets.get("gcp_service_account")  # type: ignore
            except Exception:
                creds_info = None
            if creds_info:
                try:
                    # Авторизуемся и открываем таблицу
                    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
                    creds = Credentials.from_service_account_info(dict(creds_info), scopes=scopes)
                    gc = gspread.authorize(creds)
                    sh = gc.open_by_key(sheet_id)
                    sheet_names = [ws.title for ws in sh.worksheets()]
                    target_sheet = sheet_name
                    if target_sheet not in sheet_names:
                        # если лист за текущий месяц отсутствует — пробуем предыдущий
                        prev_month = date.month - 1 or 12
                        prev_year = date.year if date.month > 1 else date.year - 1
                        alt_sheet = get_month_sheet_name(prev_month, prev_year)
                        if alt_sheet in sheet_names:
                            target_sheet = alt_sheet
                        else:
                            raise RuntimeError("Лист для текущего или предыдущего месяца не найден в Google Sheets")
                    worksheet = sh.worksheet(target_sheet)
                    values = worksheet.get_all_values()
                    df_raw = pd.DataFrame(values)
                    if df_raw.shape[0] < 3:
                        raise RuntimeError("Недостаточно строк в Google Sheet для определения заголовков")
                    header = df_raw.iloc[2].tolist()
                    df_month_gs = pd.DataFrame(df_raw.iloc[3:].values, columns=header)
                    return df_month_gs, df_raw, target_sheet
                except Exception as gsex:
                    # Если чтение через gspread не удалось, запомним ошибку
                    download_exc = gsex
            # Если учётных данных нет — приватную таблицу загрузить нельзя
        if excel_file is None:
            err_msg = "Не удалось загрузить файл Google Sheets"
            if download_exc:
                err_msg += f": {download_exc}"
            raise RuntimeError(err_msg)
    else:
        raise RuntimeError("Не указан источник данных: требуется файл или sheet_id")
    # Если мы дошли до этого места, excel_file определён и содержит данные
    target_sheet = sheet_name
    if target_sheet not in excel_file.sheet_names:
        # переходим к предыдущему месяцу
        prev_month = date.month - 1 or 12
        prev_year = date.year if date.month > 1 else date.year - 1
        alt_sheet = get_month_sheet_name(prev_month, prev_year)
        if alt_sheet in excel_file.sheet_names:
            target_sheet = alt_sheet
        else:
            raise RuntimeError("Лист для текущего или предыдущего месяца не найден")
    # Читаем данные: строка с индексом 2 содержит заголовки
    try:
        df_month = pd.read_excel(excel_file, sheet_name=target_sheet, header=2)
    except Exception as exc:
        raise RuntimeError(f"Ошибка чтения листа '{target_sheet}': {exc}")
    df_raw = pd.read_excel(excel_file, sheet_name=target_sheet, header=None)
    return df_month, df_raw, target_sheet


def parse_transport_table(sheet_df: pd.DataFrame) -> Dict[str, float]:
    """Разбирает блок "ТРАНСПОРТ +" в таблице.

    Возвращает словарь вида ``{фамилия: сумма}`` для фамилий водителей, встречающихся
    в блоке «ТРАНСПОРТ +». Суммы берутся из столбца T (index=19) или 25, если
    в T пусто. В таблице фамилия и сумма могут быть записаны в виде ``Сулейманов Дамир ...``.

    Args:
        sheet_df: датафрейм листа, прочитанный без заголовков (header=None).

    Returns:
        dict: ключ — фамилия в нижнем регистре, значение — абсолютное число затрат.
    """
    transport_map: Dict[str, float] = {}
    # Находим начало блока по строке, содержащей «ТРАНСПОРТ»
    start_indices = sheet_df.index[sheet_df[0].astype(str).str.contains('ТРАНСПОРТ', case=False, na=False)]
    if len(start_indices) == 0:
        return transport_map
    start_idx = int(start_indices[0]) + 1
    for i in range(start_idx, sheet_df.shape[0]):
        name_val = sheet_df.at[i, 0]
        # Если строка пустая, пропускаем её, так как таблица может содержать разрывы
        if pd.isna(name_val) or str(name_val).strip() == '':
            continue
        name_str = str(name_val).strip()
        # Блок заканчивается на строках «ВСЕГО» или «ИТОГО»
        if name_str.upper() in ['ВСЕГО', 'ИТОГО']:
            break
        # Тариф находится в колонке H (index 7), масса – в колонке O (index 14)
        tariff = sheet_df.at[i, 7]
        mass = sheet_df.at[i, 14] if sheet_df.shape[1] > 14 else None
        try:
            numeric_tariff = float(tariff) if pd.notna(tariff) else 0.0
        except Exception:
            numeric_tariff = 0.0
        try:
            numeric_mass = float(mass) if pd.notna(mass) else 0.0
        except Exception:
            numeric_mass = 0.0
        cost = numeric_tariff * numeric_mass
        surname = name_str.split()[0].lower() if name_str else ''
        if surname:
            transport_map[surname] = cost
    return transport_map


def prepare_dashboard_summary(
    df: pd.DataFrame,
    clients_dict: Dict[str, Any],
    transport_map: Dict[str, float]
) -> Tuple[list, dict]:
    """Готовит сводные данные для отображения в дашборде.

    Фильтрует строки по списку клиентов, вычисляет суммарный объём и прибыль,
    находит последний номер доп. соглашения, наличие водителя, отсрочку платежа и
    транспортные расходы для каждой компании.

    Args:
        df: датафрейм с заголовками (начиная с 3‑ей строки).
        clients_dict: словарь клиентов из ``clients.json`` (ключи в нижнем регистре).
        transport_map: словарь фамилий и сумм из ``parse_transport_table``.

    Returns:
        tuple(list, dict): список словарей по компаниям и общий итоговый словарь с
            ключами ``total_volume``, ``total_profit`` и ``total_transport``.
    """
    df = df.copy()
    # нормализуем названия компаний для поиска
    df['company_key'] = df['Компания'].astype(str).str.lower().str.strip()
    df_clients = df[df['company_key'].isin(clients_dict.keys())]
    summary: list = []
    total_volume = 0.0
    total_profit = 0.0
    transport_total = 0.0
    # Фамилии водителей, встречающиеся в сделках
    surnames_in_deals: set[str] = set()
    for _, row in df_clients.iterrows():
        drv_info = row.get('Данные водителя, а/м, п/п и контактные сведения')
        if isinstance(drv_info, str) and drv_info.strip():
            surnames_in_deals.add(drv_info.strip().split()[0].lower())
    # Суммируем транспортные расходы по найденным фамилиям
    for s in surnames_in_deals:
        if s in transport_map:
            transport_total += transport_map[s]
    # Группируем по каждой компании
    for comp_key in sorted(df_clients['company_key'].unique()):
        comp_df = df_clients[df_clients['company_key'] == comp_key]
        # Последний номер доп. соглашения
        try:
            last_num = int(comp_df['№ доп контрагент'].dropna().astype(int).max())
        except Exception:
            last_num = None
        vol_sum = comp_df['кол-во отгруженного, тн'].fillna(0).sum()
        prof_sum = comp_df['Итого заработали'].fillna(0).sum()
        total_volume += vol_sum
        total_profit += prof_sum
        driver_missing = comp_df['Данные водителя, а/м, п/п и контактные сведения'].isna().any() or \
            (comp_df['Данные водителя, а/м, п/п и контактные сведения'].astype(str).str.strip() == '').any()
        # Существуют ли сделки с отсрочкой, где еще не оплачено
        pending = comp_df[(comp_df['отсрочка платежа, дн'].fillna(0) >= 1) & (comp_df['Оплачено контрагентом'].isna())]
        max_defer_days = int(pending['отсрочка платежа, дн'].max()) if not pending.empty else None
        # Транспортные расходы конкретной компании
        comp_transport = 0.0
        comp_surnames: set[str] = set()
        for drv in comp_df['Данные водителя, а/м, п/п и контактные сведения']:
            if isinstance(drv, str) and drv.strip():
                comp_surnames.add(drv.strip().split()[0].lower())
        for sn in comp_surnames:
            if sn in transport_map:
                comp_transport += transport_map[sn]
        summary.append({
            'Компания': comp_key,
            'Последний № ДС': last_num,
            'Всего отгружено, тн': round(vol_sum, 3),
            'Всего заработано': round(prof_sum, 2),
            'Водитель отсутствует': driver_missing,
            'Отсрочка, дн': max_defer_days,
            'Транспортные расходы': round(comp_transport, 2)
        })
    totals = {
        'total_volume': round(total_volume, 3),
        'total_profit': round(total_profit, 2),
        'total_transport': round(transport_total, 2)
    }
    return summary, totals


def parse_company_and_transport(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Парсит данные по компаниям и таблицу «ТРАНСПОРТ +» из необработанного датафрейма.

    В Google Sheets данные организованы таким образом:

    * Колонка A содержит названия компаний, начиная с 3‑ей строки (индекс 2).
    * Значения в колонке A идут подряд до строки, где встречается «ТРАНСПОРТ +».
      Строка с этим текстом и последующие служебные строки не входят в таблицу компаний.
    * После строки «ТРАНСПОРТ +» следует таблица транспортных услуг, которая
      продолжается до строки, начинающейся с «Трансп» (например, «Трансп Услуги»).

    Позиции столбцов (0‑индексация):
        A (0) – название компании / фамилия водителя,
        G (6) – данные водителя (в продажах),
        H (7) – цена за тонну (в таблице транспортных услуг),
        M (12) – цена за 1 т (в продажах),
        O (14) – тоннаж,
        T (19) – сумма заработка,
        U (20) – оплачено контрагентом.

    Args:
        df_raw: DataFrame, считанный без заголовков (header=None).

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            sales_df — строки продаж по компаниям с колонками
                [company, tonnage, profit, price_per_ton, paid, driver_info, row_number];
            transport_df — строки таблицы «ТРАНСПОРТ +» с колонками
                [surname, price_service, tonnage, cost].
    """
    # Списки для накопления данных
    sales_rows: list = []
    transport_rows: list = []
    # Индексы столбцов
    # Основные поля: название компании (A), данные водителя (G), цена услуги (H),
    # цена за 1 т (M), тоннаж (O), прибыль (T) и оплачено (U). Эти индексы
    # используют нулевую нумерацию столбцов.
    idx_company = 0
    idx_driver_info = 6
    idx_service_price = 7
    idx_price_per_ton = 12
    idx_tonnage = 14
    idx_profit = 19
    idx_paid = 20
    # Дополнительные индексы: номера B, F, G, которые используются для фильтрации
    # строк. Если во всех трёх колонках (B, F, G) нет данных, строка считается
    # сводной/служебной и пропускается.
    idx_B = 1
    idx_F = 5
    idx_G = 6
    # Определяем границы таблицы транспорта
    transport_start: Optional[int] = None
    transport_end: Optional[int] = None
    # Ищем строку с маркером «ТРАНСПОРТ +»
    for i, row in df_raw.iterrows():
        a_val = str(row.iloc[idx_company]) if idx_company < len(row) else ""
        if a_val.strip().upper() == "ТРАНСПОРТ +":
            transport_start = i
            break
    # Если начало найдено, ищем конец — строку, начинающуюся с «Трансп»
    if transport_start is not None:
        for j in range(transport_start + 1, len(df_raw)):
            a_val = str(df_raw.iloc[j, idx_company])
            if a_val.strip().lower().startswith("трансп"):
                transport_end = j
                break
        if transport_end is None:
            transport_end = len(df_raw)
    else:
        transport_end = None
    # Определяем диапазоны продаж и транспорта
    sales_start = 2  # первые две строки — заголовки
    sales_end = (transport_start - 1) if transport_start is not None else len(df_raw) - 1
    # Собираем продажи
    for i in range(sales_start, sales_end + 1):
        row = df_raw.iloc[i]
        row_number = i + 1
        a_val = str(row.iloc[idx_company]) if idx_company < len(row) else ""
        a_clean = a_val.strip()
        if not a_clean:
            # Если название компании не указано, пропускаем строку
            continue
        # Проверяем наличие данных в обязательных столбцах B, F, G. Если во всех
        # трёх столбцах пусто или NaN, это агрегированная строка (например,
        # сводная сумма) — такие строки исключаются из расчётов. Для проверки
        # используем индексы idx_B, idx_F, idx_G.
        def _cell_empty(val: Any) -> bool:
            return (val is None) or (isinstance(val, float) and pd.isna(val)) or (str(val).strip() == '')
        val_B = row.iloc[idx_B] if idx_B < len(row) else None
        val_F = row.iloc[idx_F] if idx_F < len(row) else None
        val_G = row.iloc[idx_G] if idx_G < len(row) else None
        # Исключаем строки, где в любом из ключевых столбцов (B, F, G) нет данных.
        # Если хотя бы один из этих столбцов пустой, строка относится к поставщику
        # или служебной сумме и не должна участвовать в расчётах по клиентам.
        if _cell_empty(val_B) or _cell_empty(val_F) or _cell_empty(val_G):
            continue
        # Преобразуем числовые значения
        def parse_float(val: Any) -> Optional[float]:
            try:
                s = str(val).strip()
                if s == '':
                    return None
                return float(s.replace(' ', '').replace(',', '.'))
            except Exception:
                return None
        sales_rows.append(
            {
                'company': a_clean,
                'tonnage': parse_float(row.iloc[idx_tonnage]) if idx_tonnage < len(row) else None,
                'profit': parse_float(row.iloc[idx_profit]) if idx_profit < len(row) else None,
                'price_per_ton': parse_float(row.iloc[idx_price_per_ton]) if idx_price_per_ton < len(row) else None,
                'paid': parse_float(row.iloc[idx_paid]) if idx_paid < len(row) else None,
                'driver_info': str(row.iloc[idx_driver_info]).strip() if idx_driver_info < len(row) and str(row.iloc[idx_driver_info]).strip() != '' else None,
                'row_number': row_number,
            }
        )
    # Собираем транспорт
    if transport_start is not None:
        # данные начинаются со строки после маркера (transport_start + 1)
        t_start = transport_start + 1
        t_end = transport_end if transport_end is not None else len(df_raw)
        for i in range(t_start, t_end):
            row = df_raw.iloc[i]
            surname_full = str(row.iloc[idx_company]).strip() if idx_company < len(row) else ""
            if not surname_full:
                continue
            # преобразование чисел
            def to_float(val: Any) -> Optional[float]:
                try:
                    return float(str(val).replace(' ', '').replace(',', '.'))
                except Exception:
                    return None
            price_service = to_float(row.iloc[idx_service_price]) if idx_service_price < len(row) else None
            tonnage_val = to_float(row.iloc[idx_tonnage]) if idx_tonnage < len(row) else None
            if price_service is not None and tonnage_val is not None:
                transport_rows.append(
                    {
                        'surname': surname_full.split()[0] if surname_full else '',
                        'price_service': price_service,
                        'tonnage': tonnage_val,
                        'cost': price_service * tonnage_val,
                    }
                )
    sales_df = pd.DataFrame(sales_rows)
    transport_df = pd.DataFrame(transport_rows)
    return sales_df, transport_df


def aggregate_company_metrics(
    sales_df: pd.DataFrame,
    transport_df: pd.DataFrame,
    *,
    company_filter: Optional[Iterable[str]] = None,
    synonyms: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Агрегирует метрики по компаниям и формирует сводные таблицы.

    Args:
        sales_df: таблица продаж (выход из ``parse_company_and_transport``).
        transport_df: таблица транспортных услуг.
        company_filter: список названий компаний, которые нужно учитывать (в
            нижнем регистре). Если ``None``, учитываются все компании.
        synonyms: словарь сопоставлений сокращённых и полных названий
            (ключ — вариант в нижнем регистре, значение — желаемое отображение).

    Returns:
        Dict[str, Any]:
            {
                "summary": DataFrame — сводка по компаниям с колонками
                    [company, tonnage, profit, transport_cost, net_profit],
                "debt_table": DataFrame — задолженность/переплата по компаниям,
                "attention": DataFrame — строки, где тоннаж пустой или ≤ 0,
                "missing_driver": DataFrame — строки без указания водителя,
                "transport_details": DataFrame — сведения по совпавшим перевозкам.
            }
    """
    # Копия исходных данных
    df = sales_df.copy()
    # Нормализуем названия компаний
    df['company_lower'] = df['company'].astype(str).str.lower().str.strip()
    # Применяем словарь синонимов (если предоставлен)
    if synonyms:
        df['company_mapped'] = df['company_lower'].apply(lambda x: synonyms.get(x, x))
    else:
        df['company_mapped'] = df['company_lower']
    # Фильтруем по списку компаний
    if company_filter is not None:
        filter_set = {c.lower() for c in company_filter}
        df = df[df['company_mapped'].isin(filter_set)]
    # Парсим таблицу транспортных услуг: создаём ключ (surname, tonnage)
    transport_df = transport_df.copy()
    if not transport_df.empty:
        transport_df['surname_lower'] = transport_df['surname'].astype(str).str.lower().str.strip()
        transport_df['tonnage'] = pd.to_numeric(transport_df['tonnage'], errors='coerce')
    # Считаем стоимость услуги для каждой строки продаж
    def match_transport_cost(row: pd.Series) -> float:
        """Находит стоимость услуги для строки продаж.
        Ищет совпадение по фамилии и тоннажу. Если найдено несколько, берёт сумму.
        """
        driver = row.get('driver_info')
        ton = row.get('tonnage')
        if not isinstance(driver, str) or not driver.strip() or not pd.notna(ton):
            return 0.0
        surname = driver.strip().split()[0].lower()
        # Найти строки в транспортной таблице с такой фамилией и той же массой (или близкой)
        if transport_df.empty:
            return 0.0
        # В некоторых случаях тоннаж в транспортной таблице может отличаться
        # за счёт округления. Будем считать совпадением, если разница менее 1 тн.
        matches = transport_df[
            (transport_df['surname_lower'] == surname)
            & (transport_df['tonnage'].sub(ton).abs() < 1.0)
        ]
        if matches.empty:
            return 0.0
        return float(matches['cost'].sum())
    df['transport_cost'] = df.apply(match_transport_cost, axis=1)
    # Вычисляем чистую прибыль: profit - transport_cost
    # Чистая прибыль = прибыль - транспортные расходы
    df['net_profit'] = (
        df['profit'].fillna(0) - df['transport_cost'].fillna(0)
    )
    # Вычисляем задолженность/переплату для каждой строки: tonnage * price_per_ton - paid
    def calc_debt(row: pd.Series) -> float:
        tonnage = row.get('tonnage')
        price_per_ton = row.get('price_per_ton')
        paid = row.get('paid')
        if pd.notna(tonnage) and pd.notna(price_per_ton):
            amount = tonnage * price_per_ton
        else:
            amount = 0.0
        if pd.notna(paid):
            amount -= paid
        return float(amount)
    df['debt'] = df.apply(calc_debt, axis=1)
    # Агрегация по компаниям
    grouped = df.groupby('company_mapped').agg(
        company=('company', 'first'),
        tonnage=('tonnage', 'sum'),
        profit=('profit', 'sum'),
        transport_cost=('transport_cost', 'sum'),
        net_profit=('net_profit', 'sum'),
        debt=('debt', 'sum'),
    ).reset_index(drop=True)
    # Заполняем отсутствующие значения нулями
    for col in ['tonnage', 'profit', 'transport_cost', 'net_profit', 'debt']:
        grouped[col] = grouped[col].fillna(0.0)
    # Сводка задолженности/переплат
    debt_table = grouped[['company', 'debt']].copy()
    # Строки, требующие внимания (тоннаж <= 0 или NaN)
    attention_df = df[(df['tonnage'].isna()) | (df['tonnage'] <= 0)].copy()
    # Строки без указания водителя
    missing_driver_df = df[df['driver_info'].isna() | (df['driver_info'].astype(str).str.strip() == '')].copy()
    return {
        'summary': grouped,
        'debt_table': debt_table,
        'attention': attention_df,
        'missing_driver': missing_driver_df,
        'transport_details': transport_df,
    }