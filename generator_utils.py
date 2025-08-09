"""
Модуль generator_utils содержит функции и константы,
необходимые для генерации дополнительных соглашений
по шаблонам Word. Основной функцией модуля является
``generate_document`` — она принимает параметры договора,
подставляет значения в шаблон и возвращает данные файла.

Функции и данные вынесены из основного приложения для
повышения читаемости и возможности многократного использования.
"""

from __future__ import annotations

import os
import io
import json
import datetime
from typing import Tuple, Optional

from docxtpl import DocxTemplate
from num2words import num2words

from data_utils import load_dictionaries


# -- Базисы (условия передачи товара)
BASISES = {
    "самовывоз": "франко-автотранспортное средство Покупателя на складе Поставщика.",
    "доставка": "франко-автотранспортное средство Поставщика на складе Покупателя.",
    "нефтебаза": "франко-автотранспортное средство Покупателя на складе Поставщика."
}

# -- Названия месяцев в различных падежах
MONTHS_GENITIVE = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня',
    7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}
MONTHS_PREPOSITIONAL = {
    1: 'январе', 2: 'феврале', 3: 'марте', 4: 'апреле', 5: 'мае', 6: 'июне',
    7: 'июле', 8: 'августе', 9: 'сентябре', 10: 'октябре', 11: 'ноябре', 12: 'декабре'
}


def generate_document(
    dop_num: str,
    client_key: str,
    product_key: str,
    price_str: str,
    tons_str: str,
    pay_date: datetime.date,
    delivery_method: str,
    pickup_location: Optional[str] = None,
    delivery_address: Optional[str] = None,
    neftebaza_location: Optional[str] = None,
    document_type: str = "prepayment",
    base_dir: Optional[str] = None
) -> Tuple[Optional[bytes], Optional[bytes], Optional[str], Optional[str]]:
    """Генерирует документ Word на основе шаблона и входных данных.

    Args:
        dop_num: номер дополнительного соглашения.
        client_key: ключ клиента (строка).
        product_key: ключ продукта (строка).
        price_str: цена за тонну (строка).
        tons_str: количество тонн (строка).
        pay_date: дата оплаты.
        delivery_method: способ передачи ("самовывоз", "доставка" или "нефтебаза").
        pickup_location: пункт самовывоза (для "самовывоз").
        delivery_address: адрес доставки (для "доставка").
        neftebaza_location: название нефтебазы (для "нефтебаза").
        document_type: вид шаблона ("prepayment" или "deferment_pay").
        base_dir: директория, относительно которой искать шаблоны и словари.

    Returns:
        tuple(docx_data, pdf_data, filename_base, error_message):
            docx_data — байты созданного документа,
            pdf_data — в текущей версии None,
            filename_base — базовое имя файла без расширения,
            error_message — текст ошибки или None при успехе.
    """
    try:
        # Загружаем словари
        clients, products, locations, neftebazy = load_dictionaries(base_dir)
        # Определяем шаблон
        template_filename = f"{document_type}.docx"
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, template_filename)
        if not os.path.exists(template_path):
            return None, None, None, f"Ошибка: шаблон '{template_filename}' не найден."
        # Проверяем наличие данных в словарях
        client_data = clients.get(client_key.lower())
        product_name = products.get(product_key.lower())
        errors = []
        if not client_data:
            errors.append(f"клиент '{client_key}'")
        if not product_name:
            errors.append(f"товар '{product_key}'")
        # Определяем базис и адрес
        if delivery_method == "самовывоз":
            if not pickup_location:
                errors.append("не выбрана локация для самовывоза")
            else:
                location_full = locations.get(pickup_location.lower())
                if not location_full:
                    errors.append(f"адрес '{pickup_location}'")
                basis_full = BASISES["самовывоз"]
                location_display_name = pickup_location.capitalize()
        elif delivery_method == "нефтебаза":
            if not neftebaza_location:
                errors.append("не выбрана нефтебаза")
            else:
                location_full = neftebazy.get(neftebaza_location.lower())
                if not location_full:
                    errors.append(f"нефтебаза '{neftebaza_location}'")
                basis_full = BASISES["нефтебаза"]
                location_display_name = "Нефтебаза"
        else:  # доставка
            if not delivery_address or not delivery_address.strip():
                errors.append("не указан адрес доставки")
            else:
                location_full = delivery_address.strip()
                basis_full = BASISES["доставка"]
                location_display_name = "Доставка"
        if errors:
            return None, None, None, f"Ошибка: не найдены данные для: {', '.join(errors)}."
        # Преобразуем числовые значения
        try:
            tons = int(tons_str)
            price = int(price_str)
        except ValueError:
            return None, None, None, "Ошибка: количество тонн и цена должны быть целыми числами."
        # Формируем дату текущую
        now = datetime.datetime.now()
        current_date = f"«{now.day}» {MONTHS_GENITIVE[now.month]} {now.year}г."
        # Формируем строку месяца оплаты
        delivery_month = f"в {MONTHS_PREPOSITIONAL[pay_date.month]} {pay_date.year} г."
        # Контекст шаблона
        context = {
            'dop_num': dop_num,
            'contract': client_data.get('contract'),
            'current_date': current_date,
            'company_name': client_data.get('company_name'),
            'director_position': client_data.get('director_position'),
            'director_fio': client_data.get('director_fio'),
            'delivery_month_year': delivery_month,
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
        # Имя файла
        product_display = product_key.upper()
        if delivery_method == "самовывоз":
            filename_base = f"Дополнительное соглашение №{dop_num} {product_display} {location_display_name} Самовывоз"
        elif delivery_method == "нефтебаза":
            filename_base = f"Дополнительное соглашение №{dop_num} {product_display} Нефтебаза"
        else:
            filename_base = f"Дополнительное соглашение №{dop_num} {product_display} Доставка"
        # Сохраняем DOCX в байтовый буфер
        docx_buffer = io.BytesIO()
        doc.save(docx_buffer)
        docx_data = docx_buffer.getvalue()
        docx_buffer.close()
        # PDF не используется в Streamlit версии
        return docx_data, None, filename_base, None
    except Exception as exc:
        return None, None, None, f"Неизвестная ошибка: {exc}"