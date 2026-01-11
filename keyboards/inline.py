"""
Inline клавиатуры
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 Товары", callback_data="products_menu"),
        InlineKeyboardButton(text="💸 Расходы", callback_data="add_expense"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="🧮 Калькулятор", callback_data="calculator"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="statistics_menu"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu")
    )
    return builder.as_markup()


def get_products_menu() -> InlineKeyboardMarkup:
    """Меню товаров"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Список товаров", callback_data="list_products")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    return builder.as_markup()


def get_categories_keyboard(categories: List[Dict], action: str = "select") -> InlineKeyboardMarkup:
    """
    Клавиатура с категориями
    action: 'select' - выбор категории, 'list' - просмотр товаров
    """
    builder = InlineKeyboardBuilder()

    # Категории по 2 в ряд
    for i in range(0, len(categories), 2):
        row_buttons = []
        for j in range(2):
            if i + j < len(categories):
                category = categories[i + j]
                callback_data = f"{action}_category:{category['id']}"
                row_buttons.append(
                    InlineKeyboardButton(text=category['name'], callback_data=callback_data)
                )
        builder.row(*row_buttons)

    if action == "select":
        builder.row(
            InlineKeyboardButton(text="➕ Новая категория", callback_data="new_category")
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="products_menu")
    )

    return builder.as_markup()


def get_products_keyboard(products: List[Dict], category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с товарами категории"""
    builder = InlineKeyboardBuilder()

    for product in products:
        # Показываем полное название товара
        display_text = f"📦 {product['name']} — {product['selling_price']:.0f}₽"

        # Если название очень длинное (больше 60 символов), обрезаем только для отображения
        if len(display_text) > 64:
            display_text = f"📦 {product['name'][:50]}... — {product['selling_price']:.0f}₽"

        builder.row(
            InlineKeyboardButton(
                text=display_text,
                callback_data=f"view_product:{product['id']}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔙 К категориям", callback_data="list_products")
    )

    return builder.as_markup()


def get_product_card_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура карточки товара"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Продано", callback_data=f"sell_product:{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изм. Цену/Инфо", callback_data=f"edit_product:{product_id}"),
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_product:{product_id}"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К списку", callback_data="back_to_category_list")
    )
    return builder.as_markup()


def get_edit_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура редактирования товара"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💵 Цена закупки",
            callback_data=f"edit_purchase:{product_id}"
        ),
        InlineKeyboardButton(
            text="💰 Цена продажи",
            callback_data=f"edit_selling:{product_id}"
        ),
        width=2
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Название/Фото",
            callback_data=f"edit_info:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"view_product:{product_id}")
    )
    return builder.as_markup()


def get_confirm_delete_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete:{product_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_product:{product_id}"),
        width=2
    )
    return builder.as_markup()


def get_statistics_menu() -> InlineKeyboardMarkup:
    """Меню статистики"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="stats:day"),
        InlineKeyboardButton(text="📆 Месяц", callback_data="stats:month"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="📊 Всё время", callback_data="stats:all")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    return builder.as_markup()


def get_stats_export_keyboard(period: str) -> InlineKeyboardMarkup:
    """Клавиатура экспорта статистики"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📄 Скачать PDF", callback_data=f"export_pdf:{period}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="statistics_menu")
    )
    return builder.as_markup()


def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Изменить комиссию", callback_data="change_commission")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")
    )
    return builder.as_markup()

def get_statistics_menu() -> InlineKeyboardMarkup:
    """Меню статистики"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="stats:day"),
        InlineKeyboardButton(text="📆 Месяц", callback_data="stats:month"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="📊 Всё время", callback_data="stats:all")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Произвольный период", callback_data="stats:custom")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    )
    return builder.as_markup()


def get_date_input_method_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа ввода даты"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Выбрать через календарь", callback_data="date_method:calendar")
    )
    builder.row(
        InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="date_method:manual")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="statistics_menu")
    )
    return builder.as_markup()