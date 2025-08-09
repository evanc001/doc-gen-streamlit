"""
Файл Streamlit приложения для генерации дополнительных соглашений и отображения дашборда.

Этот модуль объединяет функциональность оригинального генератора документов
(основанного на шаблонах Word) и расширяет его дашбордом, который подключается
к Google Sheets, чтобы показать статистику по сделкам за последний месяц.

Чтобы использовать этот файл вместо исходного ``main.py`` в проекте,
замените оригинальный файл или импортируйте и запустите функцию ``main()``.
"""

import os
import json
import streamlit as st
from datetime import datetime, date
from docxtpl import DocxTemplate
from num2words import num2words
from docx2pdf import convert
import io
import pandas as pd
import requests
from functools import lru_cache


# --- 1. ЗАГРУЗКА СЛОВАРЕЙ ИЗ JSON ---

def load_json_dict(filename: str):
    """Загружает словарь из JSON файла."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл {filename} не найден!")
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка: Неверный формат JSON в файле {filename}!")
        return {}


def load_dictionaries():
    """Загружает все словари из JSON файлов, расположенных в подкаталоге ``json``."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, "json")
    clients = load_json_dict(os.path.join(json_path, "clients.json"))
    products = load_json_dict(os.path.join(json_path, "products.json"))
    locations = load_json_dict(os.path.join(json_path, "locations.json"))
    neftebazy = load_json_dict(os.path.join(json_path, "nb.json"))
    return clients, products, locations, neftebazy


# Статичные словари остаются в коде
BASISES = {
    "самовывоз": "франко-автотранспортное средство Покупателя на складе Поставщика.",
    "доставка": "франко-автотранспортное средство Поставщика на складе Покупателя.",
    "нефтебаза": "франко-автотранспортное средство Покупателя на складе Поставщика."
}

# Словари для форматирования дат
MONTHS_GENITIVE = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня',
    7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}

MONTHS_PREPOSITIONAL = {
    1: 'январе', 2: 'феврале', 3: 'марте', 4: 'апреле', 5: 'мае', 6: 'июне',
    7: 'июле', 8: 'августе', 9: 'сентябре', 10: 'октябре', 11: 'ноябре', 12: 'декабре'
}


# --- 2. ФУНКЦИИ ГЕНЕРАЦИИ ДОКУМЕНТОВ ---

def generate_document_new(
    dop_num: str,
    client_key: str,
    product_key: str,
    price_str: str,
    tons_str: str,
    pay_date: date,
    delivery_method: str,
    pickup_location: str = None,
    delivery_address: str = None,
    neftebaza_location: str = None,
    document_type: str = "prepayment",
) -> tuple:
    """Генерирует документ Word на основе отдельных параметров.

    Args:
        dop_num: Номер дополнительного соглашения.
        client_key: ключ клиента.
        product_key: ключ продукта.
        price_str: цена за тонну (строка).
        tons_str: количество тонн (строка).
        pay_date: дата оплаты (объект ``date``).
        delivery_method: один из «самовывоз», «доставка», «нефтебаза».
        pickup_location: локация для самовывоза.
        delivery_address: адрес доставки.
        neftebaza_location: нефтебаза для отгрузки.
        document_type: тип документа («prepayment» или «deferment_pay»).

    Returns:
        tuple: (docx_data, pdf_data, filename_base, error_message). ``docx_data`` содержит
        байты файла, ``pdf_data`` — None (пока PDF не используется в веб-версии),
        ``filename_base`` — базовое имя файла без расширения, ``error_message`` — текст ошибки или None.
    """
    try:
        # Загружаем словари
        clients, products, locations, neftebazy = load_dictionaries()
        # Определяем шаблон
        template_filename = f"{document_type}.docx"
        base_path = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_path, template_filename)
        if not os.path.exists(template_path):
            return None, None, None, f"Ошибка: Шаблон '{template_filename}' не найден. Убедитесь, что он находится в корневой папке скрипта."
        # Проверяем данные в словарях
        client_data = clients.get(client_key.lower())
        product_name = products.get(product_key.lower())
        errors = []
        if not client_data:
            errors.append(f"клиент '{client_key}'")
        if not product_name:
            errors.append(f"товар '{product_key}'")
        # Определяем базис и адрес в зависимости от способа доставки
        if delivery_method == "самовывоз":
            if not pickup_location:
                errors.append("не выбрана локация для самовывоза")
            else:
                location_full = locations.get(pickup_location.lower())
                if not location_full:
                    errors.append(f"адрес '{pickup_location}'")
                basis_full = BASISES["самовывоз"]
                location_display_name = pickup_location.capitalize()
                delivery_method_display = "Самовывоз"
        elif delivery_method == "нефтебаза":
            if not neftebaza_location:
                errors.append("не выбрана нефтебаза")
            else:
                location_full = neftebazy.get(neftebaza_location.lower())
                if not location_full:
                    errors.append(f"нефтебаза '{neftebaza_location}'")
                basis_full = BASISES["нефтебаза"]
                location_display_name = "Нефтебаза"
                delivery_method_display = "Нефтебаза"
        else:  # доставка
            if not delivery_address or not delivery_address.strip():
                errors.append("не указан адрес доставки")
            else:
                location_full = delivery_address.strip()
                basis_full = BASISES["доставка"]
                location_display_name = "Доставка"
                delivery_method_display = "Доставка"
        if errors:
            return None, None, None, f"Ошибка: не найдены данные в словарях для: {', '.join(errors)}.\nПроверьте правильность написания и наличие данных в JSON файлах."
        # Конвертируем числовые значения
        try:
            tons = int(tons_str)
            price = int(price_str)
        except ValueError:
            return None, None, None, f"Ошибка: количество тонн ('{tons_str}') и цена ('{price_str}') должны быть целыми числами."
        # Формируем дату создания документа
        now = datetime.now()
        current_date_month = MONTHS_GENITIVE[now.month]
        current_date_str = f"«{now.day}» {current_date_month} {now.year}г."
        # Формируем месяц и год поставки
        delivery_month_name = MONTHS_PREPOSITIONAL[pay_date.month]
        delivery_month_year = f"в {delivery_month_name} {pay_date.year} г."
        # Формируем контекст для шаблона
        context = {
            'dop_num': dop_num,
            'contract': client_data.get('contract'),
            'current_date': current_date_str,
            'company_name': client_data.get('company_name'),
            'director_position': client_data.get('director_position'),
            'director_fio': client_data.get('director_fio'),
            'delivery_month_year': delivery_month_year,
            'product_name': product_name,
            'tons_full': f"{tons} ({num2words(tons, lang='ru')})",
            'price_full': f"{price:,} ({num2words(price, lang='ru')})".replace(',', ' '),
            'basis_full': basis_full,
            'location_full': location_full,
            'pay_date': pay_date.strftime('%d.%m.%Y'),
            'initials': client_data.get('initials'),
        }
        # Генерируем документ
        doc = DocxTemplate(template_path)
        doc.render(context)
        # Формируем имя файла
        product_display = product_key.upper()
        if delivery_method == "самовывоз":
            filename_base = f"Дополнительное соглашение №{dop_num} {product_display} {location_display_name} Самовывоз"
        elif delivery_method == "нефтебаза":
            filename_base = f"Дополнительное соглашение №{dop_num} {product_display} Нефтебаза"
        else:
            filename_base = f"Дополнительное соглашение №{dop_num} {product_display} Доставка"
        # Сохраняем DOCX в память (с расширением .doc)
        docx_buffer = io.BytesIO()
        doc.save(docx_buffer)
        docx_data = docx_buffer.getvalue()
        docx_buffer.close()
        return docx_data, None, filename_base, None
    except Exception as exc:
        return None, None, None, f"Неизвестная ошибка: {exc}"


# --- 3. ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ДАШБОРДА ---

def get_month_sheet_name(month: int, year: int) -> str:
    """Возвращает название листа "МЕСЯЦ ГОД" на русском языке."""
    months = {
        1: 'ЯНВАРЬ', 2: 'ФЕВРАЛЬ', 3: 'МАРТ', 4: 'АПРЕЛЬ', 5: 'МАЙ', 6: 'ИЮНЬ',
        7: 'ИЮЛЬ', 8: 'АВГУСТ', 9: 'СЕНТЯБРЬ', 10: 'ОКТЯБРЬ', 11: 'НОЯБРЬ', 12: 'ДЕКАБРЬ'
    }
    return f"{months.get(month, '')} {year}"


@lru_cache(maxsize=2)
def download_google_sheet(sheet_id: str) -> pd.ExcelFile:
    """Загружает таблицу Google Sheets в формате Excel.

    Пытается скачать файл по прямой ссылке ``export?format=xlsx``. В случае
    неудачи пытается открыть локальный файл ``{sheet_id}.xlsx``.
    Результат кэшируется, чтобы избежать повторных загрузок.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return pd.ExcelFile(io.BytesIO(resp.content))
    except Exception:
        local_path = f"{sheet_id}.xlsx"
        if os.path.exists(local_path):
            return pd.ExcelFile(local_path)
        raise RuntimeError("Не удалось загрузить файл Google Sheets")


def parse_transport_table(sheet_df: pd.DataFrame) -> dict:
    """Разбирает таблицу "ТРАНСПОРТ +" и возвращает словарь сумм по фамилиям."""
    transport_map: dict = {}
    # Поиск строки, содержащей "ТРАНСПОРТ"
    start_indices = sheet_df.index[sheet_df[0].astype(str).str.contains('ТРАНСПОРТ', case=False, na=False)]
    if len(start_indices) == 0:
        return transport_map
    start_idx = int(start_indices[0]) + 1
    for i in range(start_idx, sheet_df.shape[0]):
        name = sheet_df.at[i, 0]
        if pd.isna(name):
            break
        name_str = str(name).strip()
        if name_str.upper() in ['ВСЕГО', 'ИТОГО']:
            break
        # Считываем значение из колонки T (index=19) или, если пусто, из 25
        value = sheet_df.at[i, 19] if not pd.isna(sheet_df.at[i, 19]) else sheet_df.at[i, 25]
        try:
            numeric_value = abs(float(value)) if pd.notna(value) else 0.0
        except Exception:
            numeric_value = 0.0
        surname = name_str.split()[0].lower()
        transport_map[surname] = numeric_value
    return transport_map


def prepare_dashboard_summary(df: pd.DataFrame, clients_dict: dict, transport_map: dict) -> tuple:
    """Подготавливает сводные данные для дашборда.

    Возвращает список словарей по каждой компании и общие итоги.
    """
    df = df.copy()
    df['company_key'] = df['Компания'].astype(str).str.lower().str.strip()
    df_clients = df[df['company_key'].isin(clients_dict.keys())]
    summary = []
    total_volume = 0.0
    total_profit = 0.0
    transport_total = 0.0
    # Собираем все фамилии водителей из сделок
    surnames_in_deals = set()
    for _, row in df_clients.iterrows():
        drv_info = row.get('Данные водителя, а/м, п/п и контактные сведения')
        if isinstance(drv_info, str) and drv_info.strip():
            surnames_in_deals.add(drv_info.strip().split()[0].lower())
    # Суммируем транспортные расходы по фамилиям
    for s in surnames_in_deals:
        if s in transport_map:
            transport_total += transport_map[s]
    # Группировка по компаниям
    for comp_key in sorted(df_clients['company_key'].unique()):
        comp_df = df_clients[df_clients['company_key'] == comp_key]
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
        pending = comp_df[(comp_df['отсрочка платежа, дн'].fillna(0) >= 1) & (comp_df['Оплачено контрагентом'].isna())]
        max_defer_days = int(pending['отсрочка платежа, дн'].max()) if not pending.empty else None
        # Транспортные расходы конкретной компании
        comp_transport = 0.0
        comp_surnames = set()
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


def dashboard_app():
    """Отображает дашборд на второй вкладке приложения."""
    st.subheader("📊 Дашборд по сделкам (последний месяц)")
    sheet_id = "1dmVVn25GQNCcCSJeh3xGx1Aics-C1PCwaYyIPgkFVKA"
    today = datetime.now()
    sheet_name = get_month_sheet_name(today.month, today.year)
    try:
        excel_file = download_google_sheet(sheet_id)
    except Exception as e:
        st.error(f"❌ Ошибка загрузки данных: {e}")
        return
    # если лист не найден — берем предыдущий месяц
    if sheet_name not in excel_file.sheet_names:
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        sheet_name = get_month_sheet_name(prev_month, prev_year)
        if sheet_name not in excel_file.sheet_names:
            st.info("Невозможно найти лист для текущего или предыдущего месяца")
            return
    # Считываем данные: строка с индексом 2 содержит заголовки
    try:
        df_month = pd.read_excel(excel_file, sheet_name=sheet_name, header=2)
    except Exception as e:
        st.error(f"❌ Ошибка чтения листа '{sheet_name}': {e}")
        return
    df_raw = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
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


# --- 4. ИНТЕРФЕЙС STREAMLIT ---

def streamlit_app():
    """Создает интерфейс Streamlit для генерации документов и просмотра дашборда."""
    st.set_page_config(page_title="Генератор доп соглашений", layout="wide")
    st.markdown("""<h2 style='text-align:center;'>🔄 Генератор дополнительных соглашений</h2>""", unsafe_allow_html=True)
    st.markdown("---")
    clients, products, locations, neftebazy = load_dictionaries()
    # Вкладки
    tab_gen, tab_dash = st.tabs(["Генератор", "Дашборд"])
    with tab_gen:
        # Боковая панель
        with st.sidebar:
            st.header("📋 Справочная информация")
            if clients:
                st.subheader("Доступные компании:")
                for key in sorted(clients.keys()):
                    st.text(f"• {key}")
            if products:
                st.subheader("Доступные товары:")
                for key in sorted(products.keys()):
                    st.text(f"• {key}")
            if locations:
                st.subheader("Доступные базисы:")
                for key in sorted(locations.keys()):
                    st.text(f"• {key}")
            if neftebazy:
                st.subheader("Доступные нефтебазы:")
                for key in sorted(neftebazy.keys()):
                    st.text(f"• {key}")
        # Выбор параметров
        st.subheader("🎯 Выбор типа документа")
        col_a, col_b = st.columns(2)
        with col_a:
            document_type = st.radio(
                "Тип оплаты:",
                options=["prepayment", "deferment_pay"],
                format_func=lambda x: "Предоплата" if x == "prepayment" else "Отсрочка платежа",
                horizontal=True,
                index=0
            )
        with col_b:
            pay_date = st.date_input(
                "Дата оплаты:",
                value=datetime.now().date(),
                help="Выберите дату оплаты"
            )
        st.markdown("---")
        st.subheader("🚚 Способ доставки")
        delivery_method = st.radio(
            "Выберите способ доставки:",
            options=["самовывоз", "доставка", "нефтебаза"],
            format_func=lambda x: {"самовывоз": "Самовывоз", "доставка": "Доставка", "нефтебаза": "Нефтебаза"}[x],
            horizontal=True,
            index=0
        )
        pickup_location = None
        delivery_address = None
        neftebaza_location = None
        if delivery_method == "самовывоз":
            st.subheader("📍 Базис для самовывоза")
            if locations:
                pickup_location = st.selectbox(
                    "Выберите базис:",
                    options=list(locations.keys()),
                    format_func=lambda x: x.upper(),
                    index=0
                )
            else:
                st.error("❌ Не найдены доступные базисы в файле locations.json")
        elif delivery_method == "нефтебаза":
            st.subheader("📍 Выбор нефтебазы")
            if neftebazy:
                neftebaza_location = st.selectbox(
                    "Выберите нефтебазу:",
                    options=list(neftebazy.keys()),
                    format_func=lambda x: x.upper(),
                    index=0
                )
            else:
                st.error("❌ Не найдены доступные нефтебазы в файле nb.json")
        else:
            st.subheader("📍 Адрес доставки")
            delivery_address = st.text_input(
                "Введите полный адрес доставки:",
                placeholder="Например: г. Казань, ул. Абсалямова, 19",
                help="Укажите полный адрес, включая город, улицу и номер дома"
            )
        st.markdown("---")
        st.subheader("📝 Ввод основных данных")
        col_c, col_d = st.columns(2)
        with col_c:
            company_data = st.text_input(
                "Компания, номер ДС:",
                placeholder="Например: деко,212",
                help="Формат: компания,номер_дс"
            )
        with col_d:
            product_data = st.text_input(
                "Продукт, количество тонн, цена:",
                placeholder="Например: дтл,25,60500",
                help="Формат: продукт,количество,цена"
            )
        st.markdown("---")
        generate_btn = st.button("📄 Сгенерировать DOC", type="primary", use_container_width=True)
        if generate_btn:
            if not company_data or not product_data:
                st.error("❌ Пожалуйста, заполните все поля с данными")
            elif delivery_method == "доставка" and (not delivery_address or not delivery_address.strip()):
                st.error("❌ Пожалуйста, укажите адрес доставки")
            elif delivery_method == "самовывоз" and not pickup_location:
                st.error("❌ Пожалуйста, выберите базис для самовывоза")
            elif delivery_method == "нефтебаза" and not neftebaza_location:
                st.error("❌ Пожалуйста, выберите нефтебазу")
            else:
                try:
                    comp_parts = [p.strip() for p in company_data.split(',')]
                    prod_parts = [p.strip() for p in product_data.split(',')]
                    if len(comp_parts) != 2:
                        st.error("❌ Неверный формат данных компании. Ожидается: компания,номер_дс")
                    elif len(prod_parts) != 3:
                        st.error("❌ Неверный формат данных продукта. Ожидается: продукт,количество,цена")
                    else:
                        client_key, dop_num = comp_parts
                        product_key, tons_str, price_str = prod_parts
                        with st.spinner("Генерация документа..."):
                            docx_data, pdf_data, filename_base, err = generate_document_new(
                                dop_num=dop_num,
                                client_key=client_key,
                                product_key=product_key,
                                price_str=price_str,
                                tons_str=tons_str,
                                pay_date=pay_date,
                                delivery_method=delivery_method,
                                pickup_location=pickup_location,
                                delivery_address=delivery_address,
                                neftebaza_location=neftebaza_location,
                                document_type=document_type
                            )
                        if err:
                            st.error(f"❌ {err}")
                        else:
                            st.success("✅ Документ успешно создан!")
                            if docx_data:
                                st.download_button(
                                    label="📄 Скачать DOC",
                                    data=docx_data,
                                    file_name=f"{filename_base}.doc",
                                    mime="application/msword",
                                    use_container_width=True
                                )
                            # Информация о заказе
                            st.info(f"🚚 Способ доставки: {delivery_method}")
                            if delivery_method == "самовывоз":
                                st.info(f"📍 Базис: {pickup_location}")
                            elif delivery_method == "нефтебаза":
                                st.info(f"📍 Нефтебаза: {neftebaza_location}")
                            else:
                                st.info(f"📍 Адрес доставки: {delivery_address}")
                            st.info(f"📅 Дата оплаты: {pay_date.strftime('%d.%m.%Y')}")
                            st.info(f"📁 Имя файла: {filename_base}.doc")
                except Exception as exc:
                    st.error(f"❌ Ошибка при обработке данных: {exc}")
    with tab_dash:
        dashboard_app()


# --- 5. КОНСОЛЬНЫЙ ИНТЕРФЕЙС (ОПЦИОНАЛЬНО) ---

def console_app():
    """Простой консольный интерфейс, оставленный для обратной совместимости."""
    print("=" * 60)
    print("🔄 ГЕНЕРАТОР ДОПОЛНИТЕЛЬНЫХ СОГЛАШЕНИЙ")
    print("=" * 60)
    clients, products, locations, neftebazy = load_dictionaries()
    if not clients:
        print("⚠️  Внимание: Словарь клиентов пуст или не найден!")
    if not products:
        print("⚠️  Внимание: Словарь товаров пуст или не найден!")
    if not locations:
        print("⚠️  Внимание: Словарь локаций пуст или не найден!")
    if not neftebazy:
        print("⚠️  Внимание: Словарь нефтебаз пуст или не найден!")
    print("\n📋 ДОСТУПНЫЕ ОПЦИИ:")
    if clients:
        print(f"   Компании: {', '.join(sorted(clients.keys()))}")
    if products:
        print(f"   Товары: {', '.join(sorted(products.keys()))}")
    if locations:
        print(f"   Адреса: {', '.join(sorted(locations.keys()))}")
    if neftebazy:
        print(f"   Нефтебазы: {', '.join(sorted(neftebazy.keys()))}")
    print(f"   Способы передачи: {', '.join(BASISES.keys())}")
    print("\n" + "=" * 60)
    # Упрощенный ввод
    while True:
        try:
            data = input("Введите строку вида 'компания,номер_ДС,продукт,кол-во,цена,тип доставки,дата оплаты': \n").strip()
        except EOFError:
            break
        if not data:
            print("Пустой ввод. Попробуйте снова.")
            continue
        try:
            comp_key, dop_num, prod_key, tons, price, deliv_method, date_str = [x.strip() for x in data.split(',')]
            pay_date = datetime.strptime(date_str, '%d.%m.%Y').date()
        except Exception as exc:
            print(f"Ошибка разбора ввода: {exc}")
            continue
        docx_data, _, filename_base, err = generate_document_new(
            dop_num=dop_num,
            client_key=comp_key,
            product_key=prod_key,
            price_str=price,
            tons_str=tons,
            pay_date=pay_date,
            delivery_method=deliv_method,
            pickup_location=None,
            delivery_address=None,
            neftebaza_location=None,
            document_type="prepayment"
        )
        if err:
            print(err)
        else:
            print(f"Документ успешно создан: {filename_base}.doc")
        again = input("Создать еще? (y/n): ").strip().lower()
        if again not in ('y', 'yes', 'да', 'д'):
            break


# --- 6. ТОЧКА ВХОДА ---

def main():
    """Главная функция запуска приложения."""
    try:
        if 'streamlit' in globals() or 'st' in globals():
            streamlit_app()
        else:
            console_app()
    except Exception:
        console_app()


if __name__ == "__main__":
    main()