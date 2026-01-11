"""
Обработчики для работы с расходами
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.inline import get_cancel_keyboard, get_main_menu
from database import Database
from config import DATABASE_PATH
from states.forms import ExpenseForm

router = Router()
db = Database(DATABASE_PATH)


@router.callback_query(F.data == "add_expense")
async def add_expense_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления расхода"""
    await callback.message.edit_text(
        "💸 <b>Внесение расхода</b>\n\n"
        "Введите сумму расхода (в рублях):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ExpenseForm.waiting_for_amount)
    await callback.answer()


@router.message(ExpenseForm.waiting_for_amount)
async def add_expense_amount(message: Message, state: FSMContext):
    """Получение суммы расхода"""
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError

        await state.update_data(amount=amount)

        await message.answer(
            f"💸 Сумма: <b>{amount:.2f} ₽</b>\n\n"
            f"Теперь введите комментарий (на что потрачено):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(ExpenseForm.waiting_for_comment)
    except ValueError:
        await message.answer(
            "❌ Ошибка! Введите корректную сумму (например, 5000 или 5000.50):",
            parse_mode="HTML"
        )


@router.message(ExpenseForm.waiting_for_comment)
async def add_expense_comment(message: Message, state: FSMContext):
    """Получение комментария и сохранение расхода"""
    comment = message.text.strip()
    data = await state.get_data()
    amount = data['amount']

    expense_id = db.add_expense(amount, comment)

    await state.clear()

    await message.answer(
        f"✅ <b>Расход записан!</b>\n\n"
        f"💸 Сумма: {amount:.2f} ₽\n"
        f"📝 Комментарий: {comment}",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )