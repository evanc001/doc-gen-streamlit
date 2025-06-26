# === Основной скрипт (main.py) ===
import os
import json
import streamlit as st
from datetime import datetime
from docxtpl import DocxTemplate
from num2words import num2words
from docx2pdf import convert
import tempfile

# --- 1. ЗАГРУЗКА СЛОВАРЕЙ ИЗ JSON ---

def load_json_dict(filename):
    """Загружает словарь из JSON файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл {filename} не найден!")
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка: Неверный формат JSON в файле {filename}!")
        return {}

# Загружаем словари
def load_dictionaries():
    """Загружает все словари из JSON файлов"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, "json")
    
    clients = load_json_dict(os.path.join(json_path, "clients.json"))
    products = load_json_dict(os.path.join(json_path, "products.json"))
    locations = load_json_dict(os.path.join(json_path, "locations.json"))
    
    return clients, products, locations

# Статичные словари остаются в коде
BASISES = {
    "самовывоз": "франко-автотранспортное средство Покупателя на складе Поставщика.",
    "доставка": "франко-автотранспортное средство Поставщика на складе Покупателя."
}

# Словарь для даты ("«25» июня") - родительный падеж
MONTHS_GENITIVE = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня',
    7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}

# Словарь для срока поставки ("в июне") - предложный падеж
MONTHS_PREPOSITIONAL = {
    1: 'январе', 2: 'феврале', 3: 'марте', 4: 'апреле', 5: 'мае', 6: 'июне',
    7: 'июле', 8: 'августе', 9: 'сентябре', 10: 'октябре', 11: 'ноябре', 12: 'декабре'
}

# --- 2. ФУНКЦИИ ГЕНЕРАЦИИ ДОКУМЕНТОВ ---

def generate_document_new(dop_num, client_key, product_key, price_str, tons_str, pay_date, 
                         delivery_method, pickup_location=None, delivery_address=None, document_type="prepayment"):
    """
    Генерирует документ Word на основе отдельных параметров.
    
    Args:
        dop_num (str): Номер дополнительного соглашения
        client_key (str): Ключ клиента
        product_key (str): Ключ продукта
        price_str (str): Цена
        tons_str (str): Количество тонн
        pay_date (str): Дата оплаты
        delivery_method (str): "самовывоз" или "доставка"
        pickup_location (str): Локация для самовывоза (если выбран самовывоз)
        delivery_address (str): Адрес доставки (если выбрана доставка)
        document_type (str): "prepayment" или "deferment_pay"
    
    Returns:
        tuple: (docx_path, pdf_path, error_message)
    """
    try:
        # Загружаем словари
        clients, products, locations = load_dictionaries()
        
        # Определяем шаблон
        template_filename = f"{document_type}.docx"
        base_path = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_path, template_filename)
        
        if not os.path.exists(template_path):
            return None, None, f"Ошибка: Шаблон '{template_filename}' не найден. Убедитесь, что он находится в корневой папке скрипта."

        # Проверяем данные в словарях
        client_data = clients.get(client_key.lower())
        product_name = products.get(product_key.lower())
        
        errors = []
        if not client_data: errors.append(f"клиент '{client_key}'")
        if not product_name: errors.append(f"товар '{product_key}'")
        
        # Определяем базис и адрес в зависимости от способа доставки
        if delivery_method == "самовывоз":
            if not pickup_location:
                errors.append("не выбрана локация для самовывоза")
            else:
                location_full = locations.get(pickup_location.lower())
                if not location_full:
                    errors.append(f"адрес '{pickup_location}'")
                basis_full = BASISES["самовывоз"]
        else:  # доставка
            if not delivery_address or not delivery_address.strip():
                errors.append("не указан адрес доставки")
            else:
                location_full = delivery_address.strip()
                basis_full = BASISES["доставка"]
        
        if errors:
            return None, None, f"Ошибка: не найдены данные в словарях для: {', '.join(errors)}.\nПроверьте правильность написания и наличие данных в JSON файлах."

        # Конвертируем числовые значения
        try:
            tons = int(tons_str)
            price = int(price_str)
        except ValueError:
            return None, None, f"Ошибка: количество тонн ('{tons_str}') и цена ('{price_str}') должны быть целыми числами."
        
        # Формируем дату создания документа
        now = datetime.now()
        current_date_month = MONTHS_GENITIVE[now.month]
        current_date = f"«{now.day}» {current_date_month} {now.year}г."
        
        # Формируем месяц и год поставки
        try:
            pay_date_obj = datetime.strptime(pay_date, '%d.%m.%Y')
        except ValueError:
            return None, None, f"Ошибка: неверный формат даты '{pay_date}'. Используйте формат ДД.ММ.ГГГГ (например, 20.07.2025)."
        
        delivery_month_name = MONTHS_PREPOSITIONAL[pay_date_obj.month]
        delivery_month_year = f"в {delivery_month_name} {pay_date_obj.year} г."
        
        # Формируем контекст для шаблона
        context = {
            'dop_num': dop_num,
            'contract': client_data['contract'],
            'current_date': current_date,
            'company_name': client_data['company_name'],
            'director_position': client_data['director_position'],
            'director_fio': client_data['director_fio'],
            'delivery_month_year': delivery_month_year,
            'product_name': product_name,
            'tons_full': f"{tons} ({num2words(tons, lang='ru')})",
            'price_full': f"{price:,} ({num2words(price, lang='ru')})".replace(',', ' '),
            'basis_full': basis_full,
            'location_full': location_full,
            'pay_date': pay_date,
            'initials': client_data['initials'],
        }

        # Генерируем документ
        doc = DocxTemplate(template_path)
        doc.render(context)
        
        # Создаем папку для сохранения
        output_dir = os.path.join(base_path, "new_doc")
        os.makedirs(output_dir, exist_ok=True)
        
        # Определяем имена файлов
        doc_type_suffix = "предоплата" if document_type == "prepayment" else "отсрочка"
        base_filename = f"Доп.соглашение_{dop_num}_{client_key.upper()}_{doc_type_suffix}"
        
        docx_filename = f"{base_filename}.docx"
        pdf_filename = f"{base_filename}.pdf"
        
        docx_path = os.path.join(output_dir, docx_filename)
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        # Сохраняем DOCX
        doc.save(docx_path)
        
        # Конвертируем в PDF
        try:
            convert(docx_path, pdf_path)
        except Exception as e:
            print(f"Предупреждение: Не удалось создать PDF файл: {e}")
            return docx_path, None, None
        
        return docx_path, pdf_path, None

    except Exception as e:
        return None, None, f"Неизвестная ошибка: {e}"

def generate_document(input_string, document_type="prepayment"):
    """
    Генерирует документ Word на основе строки ввода и типа документа.
    Оставлена для совместимости с консольным интерфейсом.
    """
    try:
        # Загружаем словари
        clients, products, locations = load_dictionaries()
        
        # Определяем шаблон
        template_filename = f"{document_type}.docx"
        base_path = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_path, template_filename)
        
        if not os.path.exists(template_path):
            return None, None, f"Ошибка: Шаблон '{template_filename}' не найден. Убедитесь, что он находится в корневой папке скрипта."

        # Парсим входную строку
        parts = [p.strip().lower() for p in input_string.split(',')]
        if len(parts) != 8:
            return None, None, f"Ошибка: Неверное количество полей. Ожидается 8, а получено {len(parts)}.\nПравильный формат: номер ДС,компания,продукт,цена,способ передачи,количество,дата оплаты,базис"
        
        dop_num, client_key, product_key, price_str, basis_key, tons_str, pay_date, location_key = parts

        # Проверяем данные в словарях
        client_data = clients.get(client_key)
        product_name = products.get(product_key)
        location_full = locations.get(location_key)
        basis_full = BASISES.get(basis_key)
        
        errors = []
        if not client_data: errors.append(f"клиент '{client_key}'")
        if not product_name: errors.append(f"товар '{product_key}'")
        if not location_full: errors.append(f"адрес '{location_key}'")
        if not basis_full: errors.append(f"базис '{basis_key}'")
        
        if errors:
            return None, None, f"Ошибка: не найдены данные в словарях для: {', '.join(errors)}.\nПроверьте правильность написания и наличие данных в JSON файлах."

        # Конвертируем числовые значения
        try:
            tons = int(tons_str)
            price = int(price_str)
        except ValueError:
            return None, None, f"Ошибка: количество тонн ('{tons_str}') и цена ('{price_str}') должны быть целыми числами."
        
        # Формируем дату создания документа
        now = datetime.now()
        current_date_month = MONTHS_GENITIVE[now.month]
        current_date = f"«{now.day}» {current_date_month} {now.year}г."
        
        # Формируем месяц и год поставки
        try:
            pay_date_obj = datetime.strptime(pay_date, '%d.%m.%Y')
        except ValueError:
            return None, None, f"Ошибка: неверный формат даты '{pay_date}'. Используйте формат ДД.ММ.ГГГГ (например, 20.07.2025)."
        
        delivery_month_name = MONTHS_PREPOSITIONAL[pay_date_obj.month]
        delivery_month_year = f"в {delivery_month_name} {pay_date_obj.year} г."
        
        # Формируем контекст для шаблона
        context = {
            'dop_num': dop_num,
            'contract': client_data['contract'],
            'current_date': current_date,
            'company_name': client_data['company_name'],
            'director_position': client_data['director_position'],
            'director_fio': client_data['director_fio'],
            'delivery_month_year': delivery_month_year,
            'product_name': product_name,
            'tons_full': f"{tons} ({num2words(tons, lang='ru')})",
            'price_full': f"{price:,} ({num2words(price, lang='ru')})".replace(',', ' '),
            'basis_full': basis_full,
            'location_full': location_full,
            'pay_date': pay_date,
            'initials': client_data['initials'],
        }

        # Генерируем документ
        doc = DocxTemplate(template_path)
        doc.render(context)
        
        # Создаем папку для сохранения
        output_dir = os.path.join(base_path, "new_doc")
        os.makedirs(output_dir, exist_ok=True)
        
        # Определяем имена файлов
        doc_type_suffix = "предоплата" if document_type == "prepayment" else "отсрочка"
        base_filename = f"Доп.соглашение_{dop_num}_{client_key.upper()}_{doc_type_suffix}"
        
        docx_filename = f"{base_filename}.docx"
        pdf_filename = f"{base_filename}.pdf"
        
        docx_path = os.path.join(output_dir, docx_filename)
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        # Сохраняем DOCX
        doc.save(docx_path)
        
        # Конвертируем в PDF
        try:
            convert(docx_path, pdf_path)
        except Exception as e:
            print(f"Предупреждение: Не удалось создать PDF файл: {e}")
            return docx_path, None, None
        
        return docx_path, pdf_path, None

    except Exception as e:
        return None, None, f"Неизвестная ошибка: {e}"

# --- 3. STREAMLIT ИНТЕРФЕЙС ---

def streamlit_app():
    """Создает интерфейс Streamlit для генерации документов"""
    st.title("🔄 Генератор дополнительных соглашений")
    st.markdown("---")
    
    # Загружаем словари для отображения доступных опций
    clients, products, locations = load_dictionaries()
    
    # Боковая панель с информацией
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
    
    # Основной интерфейс
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎯 Выбор типа документа")
        document_type = st.radio(
            "Тип оплаты:",
            options=["prepayment", "deferment_pay"],
            format_func=lambda x: "Предоплата" if x == "prepayment" else "Отсрочка платежа",
            horizontal=True
        )
    
    with col2:
        st.subheader("💡 Подсказка")
        st.info("Выберите тип документа в зависимости от условий оплаты.")
    
    st.markdown("---")
    
    # Выбор способа доставки
    st.subheader("🚚 Способ доставки")
    delivery_method = st.radio(
        " ",
        options=["самовывоз", "доставка"],
        format_func=lambda x: "Самовывоз" if x == "самовывоз" else "Доставка",
        horizontal=True
    )
    
    # Поля в зависимости от способа доставки
    pickup_location = None
    delivery_address = None
    
    if delivery_method == "самовывоз":
        st.subheader("📍 Базис для самовывоза")
        if locations:
            pickup_location = st.selectbox(
                "Выберите базис:",
                options=list(locations.keys()),
                format_func=lambda x: x.upper()
            )
        else:
            st.error("❌ Не найдены доступные базисы в файле locations.json")
    else:  # доставка
        st.subheader("📍 Адрес доставки")
        delivery_address = st.text_input(
            "Введите полный адрес доставки:",
            placeholder="Например: г. Казань, ул. Абсалямова, 19",
            help="Укажите полный адрес, включая город, улицу и номер дома"
        )
    
    st.markdown("---")
    
    # Форма ввода данных
    st.subheader("📝 Ввод основных данных")
    
    # Показываем подсказку о новом формате ввода
    st.markdown("""
    **Новый формат ввода данных через запятую:**
    `номер доп.соглашения, компания, продукт, цена, количество, дата оплаты`
    
    **Пример:** `212, деко, дтл, 63000, 21, 20.07.2025`
    """)
    
    # Поле ввода с новым placeholder
    input_data = st.text_input(
        "Введите данные:",
        placeholder="",
        help="Введите данные через запятую в указанном порядке"
    )
    
    # Кнопка генерации
    if st.button("🚀 Сгенерировать документы", type="primary"):
        if input_data:
            # Проверяем дополнительные поля
            if delivery_method == "доставка" and (not delivery_address or not delivery_address.strip()):
                st.error("❌ Пожалуйста, укажите адрес доставки")
                return
            
            if delivery_method == "самовывоз" and not pickup_location:
                st.error("❌ Пожалуйста, выберите базис для самовывоза")
                return
            
            # Парсим входные данные
            parts = [p.strip() for p in input_data.split(',')]
            if len(parts) != 6:
                st.error(f"❌ Неверное количество полей. Ожидается 6, а получено {len(parts)}.\nПравильный формат: номер ДС,компания,продукт,цена,количество,дата оплаты")
                return
            
            dop_num, client_key, product_key, price_str, tons_str, pay_date = parts
            
            with st.spinner("Генерация документов..."):
                docx_path, pdf_path, error = generate_document_new(
                    dop_num=dop_num,
                    client_key=client_key,
                    product_key=product_key,
                    price_str=price_str,
                    tons_str=tons_str,
                    pay_date=pay_date,
                    delivery_method=delivery_method,
                    pickup_location=pickup_location,
                    delivery_address=delivery_address,
                    document_type=document_type
                )
                
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.success("✅ Документы успешно созданы!")
                    
                    col1, col2 = st.columns(2)
                    
                    # Кнопки для скачивания
                    if docx_path and os.path.exists(docx_path):
                        with col1:
                            with open(docx_path, "rb") as file:
                                st.download_button(
                                    label="📄 Скачать DOCX",
                                    data=file.read(),
                                    file_name=os.path.basename(docx_path),
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )
                    
                    if pdf_path and os.path.exists(pdf_path):
                        with col2:
                            with open(pdf_path, "rb") as file:
                                st.download_button(
                                    label="📑 Скачать PDF",
                                    data=file.read(),
                                    file_name=os.path.basename(pdf_path),
                                    mime="application/pdf"
                                )
                    
                    # Показываем информацию о созданном документе
                    st.info(f"📁 Файлы сохранены в: {os.path.dirname(docx_path)}")
                    st.info(f"🚚 Способ доставки: {delivery_method}")
                    if delivery_method == "самовывоз":
                        st.info(f"📍 Базис: {pickup_location}")
                    else:
                        st.info(f"📍 Адрес доставки: {delivery_address}")
        else:
            st.warning("⚠️ Пожалуйста, введите данные для генерации документа.")

# --- 4. КОНСОЛЬНЫЙ ИНТЕРФЕЙС ---

def console_app():
    """Консольный интерфейс для генерации документов"""
    print("=" * 60)
    print("🔄 ГЕНЕРАТОР ДОПОЛНИТЕЛЬНЫХ СОГЛАШЕНИЙ")
    print("=" * 60)
    
    # Загружаем словари для проверки
    clients, products, locations = load_dictionaries()
    
    # Проверяем, что все словари загружены
    if not clients:
        print("⚠️  Внимание: Словарь клиентов пуст или не найден!")
    if not products:
        print("⚠️  Внимание: Словарь товаров пуст или не найден!")
    if not locations:
        print("⚠️  Внимание: Словарь локаций пуст или не найден!")
    
    print("\n📋 ДОСТУПНЫЕ ОПЦИИ:")
    if clients:
        print(f"   Компании: {', '.join(sorted(clients.keys()))}")
    if products:
        print(f"   Товары: {', '.join(sorted(products.keys()))}")
    if locations:
        print(f"   Адреса: {', '.join(sorted(locations.keys()))}")
    print(f"   Способы передачи: {', '.join(BASISES.keys())}")
    
    print("\n" + "=" * 60)
    
    # Выбор типа документа
    while True:
        print("\n🎯 ВЫБОР ТИПА ДОКУМЕНТА:")
        print("1. Предоплата")
        print("2. Отсрочка платежа")
        
        choice = input("Выберите тип документа (1 или 2): ").strip()
        
        if choice == "1":
            document_type = "prepayment"
            print("✅ Выбран тип: Предоплата")
            break
        elif choice == "2":
            document_type = "deferment_pay"
            print("✅ Выбран тип: Отсрочка платежа")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
    
    print("\n" + "=" * 60)
    print("📝 ВВОД ДАННЫХ")
    print("Формат: номер ДС,компания,продукт,цена,способ передачи,количество,дата оплаты,базис")
    print("Пример: 212,деко,дтл,63000,самовывоз,21,20.07.2025,танеко")
    print("=" * 60)
    
    while True:
        input_str = input("\nВведите строку данных: ").strip()
        
        if not input_str:
            print("❌ Пустая строка. Попробуйте снова.")
            continue
        
        print("\n🔄 Генерация документов...")
        docx_path, pdf_path, error = generate_document(input_str, document_type)
        
        if error:
            print(f"\n❌ ОШИБКА: {error}")
            
            retry = input("\nПопробовать снова? (да/нет): ").strip().lower()
            if retry not in ['да', 'yes', 'y', '1']:
                break
        else:
            print(f"\n✅ УСПЕХ! Документы созданы:")
            print(f"   📄 DOCX: {docx_path}")
            if pdf_path:
                print(f"   📑 PDF:  {pdf_path}")
            else:
                print("   ⚠️  PDF: Не удалось создать (проверьте установку docx2pdf)")
            
            another = input("\nСоздать еще один документ? (да/нет): ").strip().lower()
            if another not in ['да', 'yes', 'y', '1']:
                break

# --- 5. ГЛАВНАЯ ФУНКЦИЯ ---

def main():
    """Главная функция запуска приложения"""
    # Проверяем, запущен ли Streamlit
    try:
        # Если запущен через streamlit run, то __name__ будет содержать информацию о streamlit
        if 'streamlit' in str(globals()) or 'st' in globals():
            streamlit_app()
        else:
            console_app()
    except:
        console_app()

# --- 6. ЗАПУСК СКРИПТА ---

if __name__ == "__main__":
    main()

# --- 7. ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ STREAMLIT ---

def create_sample_json_files():
    """Создает примеры JSON файлов для демонстрации"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(base_path, "json")
    os.makedirs(json_dir, exist_ok=True)
    
    # Пример clients.json с обновленным форматом company_name
    sample_clients = {
        "деко": {
            "contract": "№ 123/2024",
            "company_name": "Общество с ограниченной ответственностью «ДЕКО»",
            "director_position": "Генеральный директор",
            "director_fio": "Иванов И.И.",
            "initials": "И.И. Иванов"
        },
        "компания2": {
            "contract": "№ 456/2024", 
            "company_name": "Общество с ограниченной ответственностью «КОМПАНИЯ2»",
            "director_position": "Директор",
            "director_fio": "Петров П.П.",
            "initials": "П.П. Петров"
        }
    }
    
    sample_products = {
        "дтл": "Дизельное топливо летнее",
        "дтз": "Дизельное топливо зимнее"
    }
    
    sample_locations = {
        "танеко": "г. Нижнекамск, ул. Промышленная, 1",
        "кичуй": "г. Кичуй, ул. Заводская, 10"
    }
    
    # Сохраняем примеры файлов
    with open(os.path.join(json_dir, "clients.json"), 'w', encoding='utf-8') as f:
        json.dump(sample_clients, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(json_dir, "products.json"), 'w', encoding='utf-8') as f:
        json.dump(sample_products, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(json_dir, "locations.json"), 'w', encoding='utf-8') as f:
        json.dump(sample_locations, f, ensure_ascii=False, indent=2)

# Создаем примеры JSON файлов при первом запуске
if __name__ == "__main__" and not os.path.exists(os.path.join(os.path.dirname(__file__), "json")):
    create_sample_json_files()
    print("📁 Созданы примеры JSON файлов в папке 'json'")