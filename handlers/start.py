"""
Обработчики команды /start и главного меню
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.inline import get_main_menu, get_settings_menu
from database import Database
from config import DATABASE_PATH
from states.forms import CommissionForm
from aiogram.fsm.context import FSMContext

router = Router()
db = Database(DATABASE_PATH)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    await message.answer(
        "🏪 <b>CRM-система для товарного бизнеса</b>\n\n"
        "Добро пожаловать! Выберите действие:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    """Показать главное меню"""
    await state.clear()

    # Проверяем, есть ли фото в сообщении
    if callback.message.photo:
        # Если есть фото, удаляем и отправляем новое
        await callback.message.delete()
        await callback.message.answer(
            "🏪 <b>CRM-система для товарного бизнеса</b>\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    else:
        # Если нет фото, просто редактируем
        await callback.message.edit_text(
            "🏪 <b>CRM-система для товарного бизнеса</b>\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "settings_menu")
async def show_settings_menu(callback: CallbackQuery):
    """Показать меню настроек"""
    commission = db.get_commission()

    # Проверяем, есть ли фото
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            f"⚙️ <b>Настройки</b>\n\n"
            f"Текущая комиссия площадки: <b>{commission}%</b>",
            reply_markup=get_settings_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"⚙️ <b>Настройки</b>\n\n"
            f"Текущая комиссия площадки: <b>{commission}%</b>",
            reply_markup=get_settings_menu(),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "change_commission")
async def change_commission_start(callback: CallbackQuery, state: FSMContext):
    """Начало изменения комиссии"""
    from keyboards.inline import get_cancel_keyboard

    # Проверяем, есть ли фото
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            "💳 Введите новый процент комиссии площадки (например, 15):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "💳 Введите новый процент комиссии площадки (например, 15):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    await state.set_state(CommissionForm.waiting_for_commission)
    await callback.answer()


@router.message(CommissionForm.waiting_for_commission)
async def change_commission_finish(message: Message, state: FSMContext):
    """Завершение изменения комиссии"""
    try:
        commission = float(message.text.replace(',', '.'))
        if commission < 0 or commission > 100:
            raise ValueError

        db.set_commission(commission)
        await state.clear()
        await message.answer(
            f"✅ Комиссия успешно изменена на <b>{commission}%</b>",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректное число от 0 до 100:",
            parse_mode="HTML"
        )