"""
Обработчики для работы с товарами
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.inline import (
    get_products_menu, get_categories_keyboard, get_products_keyboard,
    get_product_card_keyboard, get_edit_product_keyboard,
    get_confirm_delete_keyboard, get_cancel_keyboard
)
from database import Database
from config import DATABASE_PATH
from states.forms import ProductForm, EditProductForm
from datetime import datetime

router = Router()
db = Database(DATABASE_PATH)

# Глобальная переменная для хранения текущей категории
user_current_category = {}


# === МЕНЮ ТОВАРОВ ===

@router.callback_query(F.data == "products_menu")
async def show_products_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню товаров"""
    await state.clear()

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            "📦 <b>Управление товарами</b>\n\n"
            "Выберите действие:",
            reply_markup=get_products_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📦 <b>Управление товарами</b>\n\n"
            "Выберите действие:",
            reply_markup=get_products_menu(),
            parse_mode="HTML"
        )
    await callback.answer()


# === ДОБАВЛЕНИЕ ТОВАРА ===

@router.callback_query(F.data == "add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления товара"""
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            "📸 Отправьте фото товара:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📸 Отправьте фото товара:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    await state.set_state(ProductForm.waiting_for_photo)
    await callback.answer()


@router.message(ProductForm.waiting_for_photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    """Получение фото товара"""
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)

    categories = db.get_categories()

    if categories:
        await message.answer(
            "📁 Выберите категорию товара:",
            reply_markup=get_categories_keyboard(categories, action="select"),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "📁 У вас пока нет категорий. Введите название новой категории:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(ProductForm.waiting_for_new_category)
        return

    await state.set_state(ProductForm.waiting_for_category)


@router.callback_query(ProductForm.waiting_for_category, F.data.startswith("select_category:"))
async def add_product_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории"""
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)

    await callback.message.edit_text(
        "✏️ Введите название товара:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ProductForm.waiting_for_name)
    await callback.answer()


@router.callback_query(ProductForm.waiting_for_category, F.data == "new_category")
async def add_product_new_category(callback: CallbackQuery, state: FSMContext):
    """Создание новой категории"""
    await callback.message.edit_text(
        "📁 Введите название новой категории:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ProductForm.waiting_for_new_category)
    await callback.answer()


@router.message(ProductForm.waiting_for_new_category)
async def add_product_new_category_name(message: Message, state: FSMContext):
    """Сохранение новой категории"""
    category_name = message.text.strip()

    if db.category_exists(category_name):
        await message.answer(
            "❌ Категория с таким названием уже существует. Введите другое название:",
            parse_mode="HTML"
        )
        return

    category_id = db.add_category(category_name)
    await state.update_data(category_id=category_id)

    await message.answer(
        f"✅ Категория '<b>{category_name}</b>' создана!\n\n"
        f"✏️ Теперь введите название товара:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ProductForm.waiting_for_name)


@router.message(ProductForm.waiting_for_name)
async def add_product_name(message: Message, state: FSMContext):
    """Получение названия товара"""
    name = message.text.strip()
    await state.update_data(name=name)

    await message.answer(
        "💵 Введите цену закупки (в рублях):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ProductForm.waiting_for_purchase_price)


@router.message(ProductForm.waiting_for_purchase_price)
async def add_product_purchase_price(message: Message, state: FSMContext):
    """Получение цены закупки"""
    try:
        purchase_price = float(message.text.replace(',', '.'))
        if purchase_price <= 0:
            raise ValueError

        await state.update_data(purchase_price=purchase_price)

        await message.answer(
            "💰 Введите цену продажи (на сайте) в рублях:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(ProductForm.waiting_for_selling_price)
    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную цену (например, 1500 или 1500.50):",
            parse_mode="HTML"
        )


@router.message(ProductForm.waiting_for_selling_price)
async def add_product_selling_price(message: Message, state: FSMContext):
    """Получение цены продажи и запрос информации о поставщике"""
    try:
        selling_price = float(message.text.replace(',', '.'))
        if selling_price <= 0:
            raise ValueError

        await state.update_data(selling_price=selling_price)

        # Спрашиваем про поставщика
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ Добавить поставщика", callback_data="add_supplier")
        )
        builder.row(
            InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_supplier")
        )

        await message.answer(
            "📋 <b>Хотите добавить информацию о поставщике?</b>\n\n"
            "Это поможет отслеживать, где вы покупаете товар",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(ProductForm.waiting_for_supplier)

    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную цену (например, 2000 или 2000.50):",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "add_supplier", ProductForm.waiting_for_supplier)
async def ask_supplier_info(callback: CallbackQuery, state: FSMContext):
    """Запрос информации о поставщике"""
    await callback.message.edit_text(
        "📝 <b>Введите информацию о поставщике</b>\n\n"
        "Формат (каждое с новой строки):\n"
        "1️⃣ Название поставщика\n"
        "2️⃣ Ссылка на товар\n\n"
        "Пример:\n"
        "<code>ООО \"Поставщик\"\n"
        "https://example.com/product</code>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ProductForm.waiting_for_supplier, F.text)
async def save_product_with_supplier(message: Message, state: FSMContext):
    """Сохранение товара с информацией о поставщике"""
    lines = message.text.strip().split('\n')

    supplier_name = lines[0].strip() if len(lines) > 0 else None
    supplier_link = lines[1].strip() if len(lines) > 1 else None

    data = await state.get_data()

    commission = db.get_commission()
    profit = data['selling_price'] - data['purchase_price'] - \
             (data['selling_price'] * commission / 100)

    product_id = db.add_product(
        category_id=data['category_id'],
        name=data['name'],
        photo_id=data['photo_id'],
        purchase_price=data['purchase_price'],
        selling_price=data['selling_price'],
        supplier_name=supplier_name,
        supplier_link=supplier_link
    )

    await state.clear()

    from keyboards.inline import get_main_menu

    supplier_info = ""
    if supplier_name or supplier_link:
        supplier_info = f"\n\n📦 <b>Поставщик:</b> {supplier_name or 'Не указан'}"
        if supplier_link:
            supplier_info += f"\n🔗 <a href='{supplier_link}'>Ссылка на товар</a>"

    await message.answer(
        f"✅ <b>Товар добавлен!</b>\n\n"
        f"📦 Название: {data['name']}\n"
        f"💵 Закупка: {data['purchase_price']:.2f} ₽\n"
        f"💰 Продажа: {data['selling_price']:.2f} ₽\n"
        f"📊 Прибыль с 1 шт: {profit:.2f} ₽"
        f"{supplier_info}",
        reply_markup=get_main_menu(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@router.callback_query(F.data == "skip_supplier", ProductForm.waiting_for_supplier)
async def skip_supplier_info(callback: CallbackQuery, state: FSMContext):
    """Пропуск добавления поставщика"""
    data = await state.get_data()

    commission = db.get_commission()
    profit = data['selling_price'] - data['purchase_price'] - \
             (data['selling_price'] * commission / 100)

    product_id = db.add_product(
        category_id=data['category_id'],
        name=data['name'],
        photo_id=data['photo_id'],
        purchase_price=data['purchase_price'],
        selling_price=data['selling_price']
    )

    await state.clear()

    from keyboards.inline import get_main_menu
    await callback.message.edit_text(
        f"✅ <b>Товар добавлен!</b>\n\n"
        f"📦 Название: {data['name']}\n"
        f"💵 Закупка: {data['purchase_price']:.2f} ₽\n"
        f"💰 Продажа: {data['selling_price']:.2f} ₽\n"
        f"📊 Прибыль с 1 шт: {profit:.2f} ₽",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# === ПРОСМОТР ТОВАРОВ ===

@router.callback_query(F.data == "list_products")
async def list_products(callback: CallbackQuery):
    """Список товаров по категориям"""
    categories = db.get_categories()

    if callback.message.photo:
        await callback.message.delete()
        if not categories:
            await callback.message.answer(
                "📦 У вас пока нет товаров.\n\n"
                "Добавьте первый товар!",
                reply_markup=get_products_menu(),
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                "📁 Выберите категорию для просмотра товаров:",
                reply_markup=get_categories_keyboard(categories, action="list"),
                parse_mode="HTML"
            )
    else:
        if not categories:
            await callback.message.edit_text(
                "📦 У вас пока нет товаров.\n\n"
                "Добавьте первый товар!",
                reply_markup=get_products_menu(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "📁 Выберите категорию для просмотра товаров:",
                reply_markup=get_categories_keyboard(categories, action="list"),
                parse_mode="HTML"
            )
    await callback.answer()


@router.callback_query(F.data.startswith("list_category:"))
async def list_category_products(callback: CallbackQuery):
    """Список товаров в категории"""
    category_id = int(callback.data.split(":")[1])
    category = db.get_category_by_id(category_id)
    products = db.get_products_by_category(category_id)

    # Сохраняем текущую категорию для пользователя
    user_current_category[callback.from_user.id] = category_id

    if not products:
        await callback.message.edit_text(
            f"📁 Категория: <b>{category['name']}</b>\n\n"
            f"В этой категории пока нет товаров.",
            reply_markup=get_categories_keyboard(db.get_categories(), action="list"),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"📁 Категория: <b>{category['name']}</b>\n\n"
            f"Выберите товар:",
            reply_markup=get_products_keyboard(products, category_id),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "back_to_category_list")
async def back_to_category_list(callback: CallbackQuery):
    """Возврат к списку товаров текущей категории"""
    user_id = callback.from_user.id

    if user_id in user_current_category:
        category_id = user_current_category[user_id]
        category = db.get_category_by_id(category_id)
        products = db.get_products_by_category(category_id)

        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                f"📁 Категория: <b>{category['name']}</b>\n\n"
                f"Выберите товар:",
                reply_markup=get_products_keyboard(products, category_id),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"📁 Категория: <b>{category['name']}</b>\n\n"
                f"Выберите товар:",
                reply_markup=get_products_keyboard(products, category_id),
                parse_mode="HTML"
            )
    else:
        await list_products(callback)

    await callback.answer()


@router.callback_query(F.data.startswith("view_product:"))
async def view_product(callback: CallbackQuery):
    """Просмотр карточки товара"""
    product_id = int(callback.data.split(":")[1])
    product = db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    commission = db.get_commission()
    profit = product['selling_price'] - product['purchase_price'] - \
             (product['selling_price'] * commission / 100)

    caption = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"📁 Категория: {product['category_name']}\n"
        f"💵 Закупка: {product['purchase_price']:.2f} ₽\n"
        f"💰 Продажа: {product['selling_price']:.2f} ₽\n"
        f"📊 Прибыль с 1 шт: {profit:.2f} ₽\n"
        f"💳 Комиссия: {commission}%"
    )

    # Добавляем информацию о поставщике если есть
    if product.get('supplier_name') or product.get('supplier_link'):
        caption += f"\n\n📦 <b>Поставщик:</b>"
        if product.get('supplier_name'):
            caption += f"\n{product['supplier_name']}"
        if product.get('supplier_link'):
            caption += f"\n🔗 <a href='{product['supplier_link']}'>Ссылка на товар</a>"

    # Проверяем, есть ли фото в текущем сообщении
    if callback.message.photo:
        # Если уже есть фото, редактируем caption
        try:
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_product_card_keyboard(product_id),
                parse_mode="HTML",
                disable_web_page_preview=False
            )
        except:
            # Если не получилось отредактировать, удаляем и отправляем заново
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=product['photo_id'],
                caption=caption,
                reply_markup=get_product_card_keyboard(product_id),
                parse_mode="HTML"
            )
    else:
        # Если нет фото, удаляем текстовое сообщение и отправляем с фото
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=product['photo_id'],
            caption=caption,
            reply_markup=get_product_card_keyboard(product_id),
            parse_mode="HTML"
        )
    await callback.answer()


# === ПРОДАЖА ТОВАРА С ВОЗМОЖНОСТЬЮ ОТМЕНЫ ===

@router.callback_query(F.data.startswith("sell_product:"))
async def sell_product(callback: CallbackQuery):
    """Моментальная продажа товара"""
    product_id = int(callback.data.split(":")[1])
    product = db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Записываем продажу
    sale_id, profit = db.add_sale(product_id)

    # Создаём клавиатуру с кнопкой отмены
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Отменить продажу", callback_data=f"cancel_sale:{sale_id}")
    )

    # Отправляем уведомление с кнопкой отмены
    await callback.message.answer(
        f"✅ <b>Продажа записана!</b>\n\n"
        f"📦 Товар: {product['name']}\n"
        f"💰 Прибыль: <b>+{profit:.2f} ₽</b>\n\n"
        f"<i>У вас есть возможность отменить эту продажу</i>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data.startswith("cancel_sale:"))
async def cancel_sale(callback: CallbackQuery):
    """Отмена продажи"""
    sale_id = int(callback.data.split(":")[1])

    # Получаем информацию о продаже
    sale = db.get_sale_by_id(sale_id)

    if not sale:
        await callback.answer("❌ Продажа не найдена", show_alert=True)
        return

    if sale['is_cancelled'] == 1:
        await callback.answer("❌ Эта продажа уже была отменена", show_alert=True)
        return

    # Отменяем продажу
    success = db.cancel_sale(sale_id)

    if success:
        # Редактируем сообщение
        await callback.message.edit_text(
            f"❌ <b>Продажа отменена</b>\n\n"
            f"📦 Товар: {sale['product_name']}\n"
            f"💸 Сумма: {sale['selling_price']:.2f} ₽\n"
            f"📊 Прибыль была: {sale['profit']:.2f} ₽\n"
            f"⏰ Дата отмены: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
        await callback.answer("✅ Продажа успешно отменена", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при отмене продажи", show_alert=True)


# === РЕДАКТИРОВАНИЕ ТОВАРА ===

@router.callback_query(F.data.startswith("edit_product:"))
async def edit_product_menu(callback: CallbackQuery):
    """Меню редактирования товара"""
    product_id = int(callback.data.split(":")[1])
    product = db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await callback.message.edit_caption(
        caption=f"✏️ Редактирование товара: <b>{product['name']}</b>\n\n"
                f"Выберите, что хотите изменить:",
        reply_markup=get_edit_product_keyboard(product_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_purchase:"))
async def edit_purchase_price_start(callback: CallbackQuery, state: FSMContext):
    """Начало изменения цены закупки"""
    product_id = int(callback.data.split(":")[1])
    await state.update_data(product_id=product_id)

    await callback.message.delete()
    await callback.message.answer(
        "💵 Введите новую цену закупки (в рублях):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(EditProductForm.waiting_for_purchase_price)
    await callback.answer()


@router.message(EditProductForm.waiting_for_purchase_price)
async def edit_purchase_price_finish(message: Message, state: FSMContext):
    """Завершение изменения цены закупки"""
    try:
        purchase_price = float(message.text.replace(',', '.'))
        if purchase_price <= 0:
            raise ValueError

        data = await state.get_data()
        product_id = data['product_id']

        db.update_product_prices(product_id, purchase_price=purchase_price)
        product = db.get_product_by_id(product_id)

        await state.clear()

        commission = db.get_commission()
        profit = product['selling_price'] - purchase_price - \
                 (product['selling_price'] * commission / 100)

        caption = (
            f"✅ <b>Цена закупки обновлена!</b>\n\n"
            f"📦 {product['name']}\n"
            f"💵 Новая цена закупки: {purchase_price:.2f} ₽\n"
            f"💰 Цена продажи: {product['selling_price']:.2f} ₽\n"
            f"📊 Прибыль с 1 шт: {profit:.2f} ₽"
        )

        await message.answer_photo(
            photo=product['photo_id'],
            caption=caption,
            reply_markup=get_product_card_keyboard(product_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную цену (например, 1500 или 1500.50):",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("edit_selling:"))
async def edit_selling_price_start(callback: CallbackQuery, state: FSMContext):
    """Начало изменения цены продажи"""
    product_id = int(callback.data.split(":")[1])
    await state.update_data(product_id=product_id)

    await callback.message.delete()
    await callback.message.answer(
        "💰 Введите новую цену продажи (в рублях):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(EditProductForm.waiting_for_selling_price)
    await callback.answer()


@router.message(EditProductForm.waiting_for_selling_price)
async def edit_selling_price_finish(message: Message, state: FSMContext):
    """Завершение изменения цены продажи"""
    try:
        selling_price = float(message.text.replace(',', '.'))
        if selling_price <= 0:
            raise ValueError

        data = await state.get_data()
        product_id = data['product_id']

        db.update_product_prices(product_id, selling_price=selling_price)
        product = db.get_product_by_id(product_id)

        await state.clear()

        commission = db.get_commission()
        profit = selling_price - product['purchase_price'] - \
                 (selling_price * commission / 100)

        caption = (
            f"✅ <b>Цена продажи обновлена!</b>\n\n"
            f"📦 {product['name']}\n"
            f"💵 Цена закупки: {product['purchase_price']:.2f} ₽\n"
            f"💰 Новая цена продажи: {selling_price:.2f} ₽\n"
            f"📊 Прибыль с 1 шт: {profit:.2f} ₽"
        )

        await message.answer_photo(
            photo=product['photo_id'],
            caption=caption,
            reply_markup=get_product_card_keyboard(product_id),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную цену (например, 2000 или 2000.50):",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("edit_info:"))
async def edit_info_start(callback: CallbackQuery, state: FSMContext):
    """Начало изменения названия"""
    product_id = int(callback.data.split(":")[1])
    await state.update_data(product_id=product_id)

    await callback.message.delete()
    await callback.message.answer(
        "✏️ Введите новое название товара:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(EditProductForm.waiting_for_name)
    await callback.answer()


@router.message(EditProductForm.waiting_for_name)
async def edit_name_finish(message: Message, state: FSMContext):
    """Завершение изменения названия"""
    name = message.text.strip()
    data = await state.get_data()
    product_id = data['product_id']

    db.update_product_info(product_id, name=name)
    product = db.get_product_by_id(product_id)

    await state.clear()

    commission = db.get_commission()
    profit = product['selling_price'] - product['purchase_price'] - \
             (product['selling_price'] * commission / 100)

    caption = (
        f"✅ <b>Название обновлено!</b>\n\n"
        f"📦 {name}\n"
        f"💵 Закупка: {product['purchase_price']:.2f} ₽\n"
        f"💰 Продажа: {product['selling_price']:.2f} ₽\n"
        f"📊 Прибыль с 1 шт: {profit:.2f} ₽"
    )

    await message.answer_photo(
        photo=product['photo_id'],
        caption=caption,
        reply_markup=get_product_card_keyboard(product_id),
        parse_mode="HTML"
    )


# === УДАЛЕНИЕ ТОВАРА ===

@router.callback_query(F.data.startswith("delete_product:"))
async def delete_product_confirm(callback: CallbackQuery):
    """Подтверждение удаления товара"""
    product_id = int(callback.data.split(":")[1])
    product = db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await callback.message.edit_caption(
        caption=f"❌ Вы уверены, что хотите удалить товар:\n<b>{product['name']}</b>?",
        reply_markup=get_confirm_delete_keyboard(product_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def delete_product_finish(callback: CallbackQuery):
    """Финальное удаление товара"""
    product_id = int(callback.data.split(":")[1])
    product = db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    db.delete_product(product_id)

    await callback.message.delete()
    from keyboards.inline import get_main_menu
    await callback.message.answer(
        f"✅ Товар '<b>{product['name']}</b>' успешно удален!",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()