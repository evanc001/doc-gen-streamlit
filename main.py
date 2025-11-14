"""
Главный модуль Streamlit приложения. Здесь объединяются
генератор дополнительных соглашений и дашборд. Код разделён
на вкладки, чтобы пользователь мог переключаться между
созданием документов и анализом данных.

Для генерации документов используется функция
``generate_document`` из ``generator_utils``. Для отображения
статистики — ``display_dashboard`` из ``dashboard``.
"""

from __future__ import annotations

import datetime
import streamlit as st

from generator_utils import generate_document, BASISES
from data_utils import load_dictionaries
from dashboard import display_dashboard
from emoji_icons import get_icon_html


def run_app() -> None:
    """Запускает веб‑приложение Streamlit."""
    # Настройки страницы
    st.set_page_config(page_title="Генератор доп. соглашений", layout="wide")
    # Инъекция пользовательских стилей (общих для всего приложения)
    # Заголовок
    st.markdown(f"""<h1 style='text-align:center;'>{get_icon_html('📝', 28)} Сервис для работы с договорами</h1>""", unsafe_allow_html=True)
    st.markdown("""<p style='text-align:center;color:gray;'>Создавайте дополнительные соглашения и анализируйте сделки в одном месте</p>""", unsafe_allow_html=True)
    st.markdown("---")
    # Загрузка словарей
    clients, products, locations, neftebazy = load_dictionaries()
    # Вкладки для генератора и дашборда
    tab_gen, tab_dash = st.tabs(["Генератор", "Дашборд"])
    with tab_gen:
        st.markdown(f"### {get_icon_html('📄', 20)} Генератор дополнительных соглашений", unsafe_allow_html=True)
        st.write("Введите данные, чтобы сформировать документ. Формат полей описан в подсказках.")
        # Боковая панель со справочной информацией
        with st.sidebar:
            st.markdown(f"## {get_icon_html('ℹ️', 24)} Справка", unsafe_allow_html=True)
            if clients:
                st.subheader("Компании")
                for key in sorted(clients.keys()):
                    st.text(f"• {key}")
            if products:
                st.subheader("Продукты")
                for key in sorted(products.keys()):
                    st.text(f"• {key}")
            if locations:
                st.subheader("Базисы самовывоза")
                for key in sorted(locations.keys()):
                    st.text(f"• {key}")
            if neftebazy:
                st.subheader("Нефтебазы")
                for key in sorted(neftebazy.keys()):
                    st.text(f"• {key}")
        # Форма генерации
        st.markdown(f"### {get_icon_html('📌', 20)} Основные параметры", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            document_type = st.radio(
                "Тип оплаты",
                options=["prepayment", "deferment_pay"],
                format_func=lambda x: "Предоплата" if x == "prepayment" else "Отсрочка платежа",
                index=0,
                horizontal=True
            )
        with col2:
            pay_date = st.date_input(
                "Дата оплаты",
                value=datetime.date.today(),
                help="Укажите плановую дату оплаты"
            )
        st.markdown(f"### {get_icon_html('🚚', 20)} Способ доставки", unsafe_allow_html=True)
        delivery_method = st.radio(
            "Способ доставки",
            options=["самовывоз", "доставка", "нефтебаза"],
            format_func=lambda x: {"самовывоз": "Самовывоз", "доставка": "Доставка", "нефтебаза": "Нефтебаза"}[x],
            index=0,
            horizontal=True
        )
        pickup_location = None
        delivery_address = None
        neftebaza_location = None
        if delivery_method == "самовывоз":
            st.markdown(f"#### {get_icon_html('📍', 18)} Выбор базиса для самовывоза", unsafe_allow_html=True)
            if locations:
                pickup_location = st.selectbox(
                    "Базис",
                    options=list(locations.keys()),
                    format_func=str.upper,
                )
            else:
                st.error("Не найдены базисы в файле locations.json")
        elif delivery_method == "нефтебаза":
            st.markdown(f"#### {get_icon_html('🛢️', 18)} Выбор нефтебазы", unsafe_allow_html=True)
            if neftebazy:
                neftebaza_location = st.selectbox(
                    "Нефтебаза",
                    options=list(neftebazy.keys()),
                    format_func=str.upper,
                )
            else:
                st.error("Не найдены нефтебазы в файле nb.json")
        else:
            st.markdown(f"#### {get_icon_html('🏠', 18)} Адрес доставки", unsafe_allow_html=True)
            delivery_address = st.text_input(
                "Адрес доставки",
                placeholder="Например: г. Казань, ул. Абсалямова, 19"
            )
        st.markdown(f"### {get_icon_html('📝', 20)} Ввод данных", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            comp_input = st.text_input(
                "Компания, номер ДС",
                placeholder="Например: деко,212",
                help="Формат: компания,номер_дс"
            )
        with col4:
            prod_input = st.text_input(
                "Продукт, количество, цена",
                placeholder="Например: дтл,25,60500",
                help="Формат: товар,количество,цена"
            )
        # Кнопка генерации
        if st.button("Сгенерировать", type="primary"):
            # Валидируем ввод
            if not comp_input or not prod_input:
                st.error("Пожалуйста, заполните все поля")
            elif delivery_method == "доставка" and (not delivery_address or not delivery_address.strip()):
                st.error("Укажите адрес доставки")
            elif delivery_method == "самовывоз" and not pickup_location:
                st.error("Выберите базис для самовывоза")
            elif delivery_method == "нефтебаза" and not neftebaza_location:
                st.error("Выберите нефтебазу")
            else:
                try:
                    comp_parts = [p.strip() for p in comp_input.split(',')]
                    prod_parts = [p.strip() for p in prod_input.split(',')]
                    if len(comp_parts) != 2:
                        st.error("Неверный формат компании. Используйте формат: компания,номер")
                    elif len(prod_parts) != 3:
                        st.error("Неверный формат продукта. Используйте формат: продукт,количество,цена")
                    else:
                        client_key, dop_num = comp_parts
                        product_key, tons_str, price_str = prod_parts
                        with st.spinner("Генерация документа..."):
                            docx_data, _, filename_base, err = generate_document(
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
                                document_type=document_type,
                                base_dir=None
                            )
                        if err:
                            st.error(err)
                        else:
                            st.success("Документ успешно создан!")
                            if docx_data:
                                st.download_button(
                                    label="Скачать DOC",
                                    data=docx_data,
                                    file_name=f"{filename_base}.doc",
                                    mime="application/msword",
                                )
                            st.info(f"Способ доставки: {delivery_method}")
                            if delivery_method == "самовывоз":
                                st.info(f"Базис: {pickup_location}")
                            elif delivery_method == "нефтебаза":
                                st.info(f"Нефтебаза: {neftebaza_location}")
                            else:
                                st.info(f"Адрес: {delivery_address}")
                            st.info(f"Дата оплаты: {pay_date.strftime('%d.%m.%Y')}")
                            st.info(f"Имя файла: {filename_base}.doc")
                except Exception as exc:
                    st.error(f"Ошибка при генерации: {exc}")
    # Вкладка дашборд
    with tab_dash:
        # Передаем идентификатор вашей Google Sheets. При необходимости можно оставить None,
        # тогда будет доступна только загрузка файла.
        display_dashboard()


def main() -> None:
    """Точка входа для запуска приложения."""
    run_app()


if __name__ == "__main__":
    main()