"""
Обработчики калькулятора прибыли
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database import Database
from config import DATABASE_PATH
from states.forms import CalculatorForm

router = Router()
db = Database(DATABASE_PATH)


def get_calculator_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура калькулятора"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Рассчитать снова", callback_data="calculator_start")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()


def get_calculator_cancel_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура отмены калькулятора"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")
    )
    return builder.as_markup()


@router.callback_query(F.data == "calculator")
async def calculator_start(callback: CallbackQuery, state: FSMContext):
    """Начало работы калькулятора"""
    commission = db.get_commission()

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            f"🧮 <b>Калькулятор прибыли</b>\n\n"
            f"Текущая комиссия площадки: <b>{commission}%</b>\n\n"
            f"💵 Введите цену закупки (в рублях):",
            reply_markup=get_calculator_cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"🧮 <b>Калькулятор прибыли</b>\n\n"
            f"Текущая комиссия площадки: <b>{commission}%</b>\n\n"
            f"💵 Введите цену закупки (в рублях):",
            reply_markup=get_calculator_cancel_keyboard(),
            parse_mode="HTML"
        )

    await state.set_state(CalculatorForm.waiting_for_purchase_price)
    await callback.answer()


@router.callback_query(F.data == "calculator_start")
async def calculator_restart(callback: CallbackQuery, state: FSMContext):
    """Перезапуск калькулятора"""
    await calculator_start(callback, state)


@router.message(CalculatorForm.waiting_for_purchase_price)
async def calculator_purchase_price(message: Message, state: FSMContext):
    """Получение цены закупки"""
    try:
        purchase_price = float(message.text.replace(',', '.'))
        if purchase_price <= 0:
            raise ValueError

        await state.update_data(purchase_price=purchase_price)

        await message.answer(
            f"💵 Цена закупки: <b>{purchase_price:.2f} ₽</b>\n\n"
            f"💰 Теперь введите цену продажи (в рублях):",
            reply_markup=get_calculator_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(CalculatorForm.waiting_for_selling_price)

    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную цену (например, 1500 или 1500.50):",
            parse_mode="HTML"
        )


@router.message(CalculatorForm.waiting_for_selling_price)
async def calculator_selling_price(message: Message, state: FSMContext):
    """Получение цены продажи и расчёт прибыли"""
    try:
        selling_price = float(message.text.replace(',', '.'))
        if selling_price <= 0:
            raise ValueError

        data = await state.get_data()
        purchase_price = data['purchase_price']

        # Получаем комиссию
        commission = db.get_commission()

        # Расчёты
        commission_amount = selling_price * commission / 100
        gross_profit = selling_price - purchase_price
        net_profit = selling_price - purchase_price - commission_amount
        margin = (net_profit / selling_price * 100) if selling_price > 0 else 0
        markup = (net_profit / purchase_price * 100) if purchase_price > 0 else 0

        await state.clear()

        # Формируем красивый отчёт
        result_text = (
            f"🧮 <b>Результаты расчёта</b>\n"
            f"{'=' * 30}\n\n"
            f"📊 <b>ИСХОДНЫЕ ДАННЫЕ:</b>\n"
            f"💵 Цена закупки: <code>{purchase_price:,.2f} ₽</code>\n"
            f"💰 Цена продажи: <code>{selling_price:,.2f} ₽</code>\n"
            f"💳 Комиссия площадки: <code>{commission}%</code>\n\n"
            f"{'=' * 30}\n\n"
            f"💸 <b>РАСЧЁТ КОМИССИИ:</b>\n"
            f"Сумма комиссии: <code>{commission_amount:,.2f} ₽</code>\n"
            f"<i>({selling_price:,.2f} × {commission}% = {commission_amount:,.2f})</i>\n\n"
            f"{'=' * 30}\n\n"
            f"📈 <b>ПРИБЫЛЬ:</b>\n"
        )

        # Валовая прибыль
        if gross_profit > 0:
            result_text += f"✅ Валовая прибыль: <b><code>+{gross_profit:,.2f} ₽</code></b>\n"
        else:
            result_text += f"❌ Валовая прибыль: <b><code>{gross_profit:,.2f} ₽</code></b>\n"

        result_text += f"<i>(Без учёта комиссии)</i>\n\n"

        # Чистая прибыль
        if net_profit > 0:
            result_text += f"💚 <b>Чистая прибыль: <code>+{net_profit:,.2f} ₽</code></b>\n"
        elif net_profit == 0:
            result_text += f"⚪️ <b>Чистая прибыль: <code>{net_profit:,.2f} ₽</code></b>\n"
        else:
            result_text += f"❌ <b>УБЫТОК: <code>{net_profit:,.2f} ₽</code></b>\n"

        result_text += f"<i>(С учётом комиссии {commission}%)</i>\n\n"
        result_text += f"{'=' * 30}\n\n"

        # Дополнительная аналитика
        result_text += f"📊 <b>АНАЛИТИКА:</b>\n"

        if margin > 0:
            result_text += f"📍 Маржа: <code>{margin:.2f}%</code>\n"
        else:
            result_text += f"📍 Маржа: <code>{margin:.2f}%</code> ⚠️\n"

        if markup > 0:
            result_text += f"📍 Наценка: <code>{markup:.2f}%</code>\n\n"
        else:
            result_text += f"📍 Наценка: <code>{markup:.2f}%</code> ⚠️\n\n"

        # Рекомендации
        result_text += f"{'=' * 30}\n\n"
        result_text += f"💡 <b>РЕКОМЕНДАЦИИ:</b>\n"

        if net_profit <= 0:
            result_text += (
                f"⚠️ Товар будет продан в убыток!\n"
                f"Рекомендуемая минимальная цена продажи:\n"
                f"<code>{purchase_price / (1 - commission / 100):,.2f} ₽</code>\n"
            )
        elif net_profit < purchase_price * 0.2:
            result_text += (
                f"⚠️ Прибыль менее 20% от закупки\n"
                f"Для прибыли 30% установите цену:\n"
                f"<code>{(purchase_price * 1.3) / (1 - commission / 100):,.2f} ₽</code>\n"
            )
        else:
            result_text += f"✅ Отличная прибыльность!\n"

        # Таблица вариантов прибыли
        result_text += f"\n{'=' * 30}\n\n"
        result_text += f"📋 <b>ВАРИАНТЫ ЦЕНЫ:</b>\n\n"

        variants = [10, 20, 30, 50]
        for percent in variants:
            target_profit = purchase_price * (percent / 100)
            target_price = (purchase_price + target_profit) / (1 - commission / 100)
            result_text += (
                f"• Прибыль {percent}%: "
                f"цена <code>{target_price:,.2f} ₽</code> "
                f"→ +<code>{target_profit:,.2f} ₽</code>\n"
            )

        await message.answer(
            result_text,
            reply_markup=get_calculator_keyboard(),
            parse_mode="HTML"
        )

    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную цену (например, 2000 или 2000.50):",
            parse_mode="HTML"
        )