"""
Обработчики для работы с товарами
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from keyboards.inline import (
    get_products_menu, get_categories_keyboard, get_products_keyboard,
    get_product_card_keyboard, get_edit_product_keyboard,
    get_confirm_delete_keyboard, get_cancel_keyboard
)
from database import Database
from config import DATABASE_PATH
from states.forms import ProductForm, EditProductForm

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
    """Получение цены продажи и сохранение товара"""
    try:
        selling_price = float(message.text.replace(',', '.'))
        if selling_price <= 0:
            raise ValueError

        data = await state.get_data()

        commission = db.get_commission()
        profit = selling_price - data['purchase_price'] - (selling_price * commission / 100)

        product_id = db.add_product(
            category_id=data['category_id'],
            name=data['name'],
            photo_id=data['photo_id'],
            purchase_price=data['purchase_price'],
            selling_price=selling_price
        )

        await state.clear()

        from keyboards.inline import get_main_menu
        await message.answer(
            f"✅ <b>Товар добавлен!</b>\n\n"
            f"📦 Название: {data['name']}\n"
            f"💵 Закупка: {data['purchase_price']:.2f} ₽\n"
            f"💰 Продажа: {selling_price:.2f} ₽\n"
            f"📊 Прибыль с 1 шт: {profit:.2f} ₽",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную цену (например, 2000 или 2000.50):",
            parse_mode="HTML"
        )


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

    # Проверяем, есть ли фото в текущем сообщении
    if callback.message.photo:
        # Если уже есть фото, редактируем caption
        try:
            await callback.message.edit_caption(
                caption=caption,
                reply_markup=get_product_card_keyboard(product_id),
                parse_mode="HTML"
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


# === ПРОДАЖА ТОВАРА ===

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

    await callback.answer(
        f"✅ Продажа '{product['name']}' записана!\nПрибыль: +{profit:.2f} ₽",
        show_alert=True
    )


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