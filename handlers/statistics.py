"""
Обработчики для статистики и отчетов
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile, Message
from aiogram.fsm.context import FSMContext
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback, get_user_locale
from keyboards.inline import (
    get_statistics_menu, get_stats_export_keyboard,
    get_main_menu, get_date_input_method_keyboard
)
from database import Database
from config import DATABASE_PATH
from utils.pdf_generator import PDFGenerator
from datetime import datetime, timedelta
from states.forms import CustomPeriodForm

router = Router()
db = Database(DATABASE_PATH)


@router.callback_query(F.data == "statistics_menu")
async def show_statistics_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню статистики"""
    await state.clear()

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            "📊 <b>Статистика и отчеты</b>\n\n"
            "Выберите период для просмотра:",
            reply_markup=get_statistics_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📊 <b>Статистика и отчеты</b>\n\n"
            "Выберите период для просмотра:",
            reply_markup=get_statistics_menu(),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("stats:"))
async def show_statistics(callback: CallbackQuery, state: FSMContext):
    """Показать статистику за период"""
    period = callback.data.split(":")[1]

    # Если выбран произвольный период
    if period == "custom":
        await callback.message.edit_text(
            "📋 <b>Произвольный период</b>\n\n"
            "Выберите способ указания дат:",
            reply_markup=get_date_input_method_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    stats = db.get_statistics(period)

    period_names = {
        'day': '📅 За сегодня',
        'month': '📆 За текущий месяц',
        'all': '📊 За всё время'
    }

    # Формирование текста отчета
    text = f"<b>{period_names[period]}</b>\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"<b>📈 ПРОДАЖИ</b>\n"
    text += f"Количество продаж: <b>{stats['total_sales']}</b> шт.\n"
    text += f"Общая выручка: <b>{stats['total_revenue']:,.2f}</b> ₽\n"
    text += f"Прибыль от продаж: <b>{stats['total_profit']:,.2f}</b> ₽\n\n"

    text += f"<b>💸 РАСХОДЫ</b>\n"
    text += f"Общие расходы: <b>{stats['total_expenses']:,.2f}</b> ₽\n\n"

    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"<b>💰 ЧИСТАЯ ПРИБЫЛЬ</b>\n"

    net_profit = stats['net_profit']
    if net_profit >= 0:
        text += f"<b>{net_profit:,.2f}</b> ₽ ✅"
    else:
        text += f"<b>{net_profit:,.2f}</b> ₽ ❌"

    # Детализация продаж
    if stats['sales']:
        text += f"\n\n<b>📦 ПРОДАННЫЕ ТОВАРЫ:</b>\n"
        for i, sale in enumerate(stats['sales'][:10], 1):
            date_str = datetime.fromisoformat(sale['sale_date']).strftime('%d.%m %H:%M')
            text += f"{i}. {sale['product_name']} - {sale['selling_price']:.2f}₽ ({date_str})\n"

        if len(stats['sales']) > 10:
            text += f"\n... и еще {len(stats['sales']) - 10} продаж"

    # Детализация расходов
    if stats['expenses']:
        text += f"\n\n<b>💸 РАСХОДЫ:</b>\n"
        for i, expense in enumerate(stats['expenses'][:5], 1):
            date_str = datetime.fromisoformat(expense['expense_date']).strftime('%d.%m %H:%M')
            text += f"{i}. {expense['comment'][:30]} - {expense['amount']:.2f}₽ ({date_str})\n"

        if len(stats['expenses']) > 5:
            text += f"\n... и еще {len(stats['expenses']) - 5} расходов"

    await callback.message.edit_text(
        text,
        reply_markup=get_stats_export_keyboard(period),
        parse_mode="HTML"
    )
    await callback.answer()


# === ПРОИЗВОЛЬНЫЙ ПЕРИОД ===

@router.callback_query(F.data.startswith("date_method:"))
async def choose_date_input_method(callback: CallbackQuery, state: FSMContext):
    """Выбор способа ввода даты"""
    method = callback.data.split(":")[1]

    if method == "calendar":
        # Используем календарь
        await callback.message.edit_text(
            "📅 <b>Выберите дату начала периода:</b>",
            reply_markup=await SimpleCalendar(locale=await get_user_locale(callback.from_user)).start_calendar(),
            parse_mode="HTML"
        )
        await state.set_state(CustomPeriodForm.waiting_for_start_date)
    else:
        # Ввод вручную
        await callback.message.edit_text(
            "⌨️ <b>Введите дату начала периода</b>\n\n"
            "Формат: ДД.ММ.ГГГГ\n"
            "Например: 01.01.2024",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        await state.set_state(CustomPeriodForm.waiting_for_start_date_manual)

    await callback.answer()


# === КАЛЕНДАРЬ - ВЫБОР НАЧАЛЬНОЙ ДАТЫ ===

@router.callback_query(SimpleCalendarCallback.filter(), CustomPeriodForm.waiting_for_start_date)
async def process_start_date_calendar(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    """Обработка выбора начальной даты через календарь"""
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user), show_alerts=True)
    calendar.set_dates_range(datetime(2020, 1, 1), datetime.now())

    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        await state.update_data(start_date=date)

        await callback.message.edit_text(
            f"✅ Дата начала: <b>{date.strftime('%d.%m.%Y')}</b>\n\n"
            f"📅 <b>Теперь выберите дату окончания периода:</b>",
            reply_markup=await SimpleCalendar(locale=await get_user_locale(callback.from_user)).start_calendar(),
            parse_mode="HTML"
        )
        await state.set_state(CustomPeriodForm.waiting_for_end_date)


# === КАЛЕНДАРЬ - ВЫБОР КОНЕЧНОЙ ДАТЫ ===

@router.callback_query(SimpleCalendarCallback.filter(), CustomPeriodForm.waiting_for_end_date)
async def process_end_date_calendar(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    """Обработка выбора конечной даты через календарь"""
    calendar = SimpleCalendar(locale=await get_user_locale(callback.from_user), show_alerts=True)

    data = await state.get_data()
    start_date = data.get('start_date')

    if start_date:
        calendar.set_dates_range(start_date, datetime.now())

    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        await state.update_data(end_date=date)

        # Получаем данные и генерируем отчет
        data = await state.get_data()
        start_date = data['start_date']
        end_date = data['end_date']

        await state.clear()

        # Получаем статистику за выбранный период
        stats = db.get_statistics_custom(start_date, end_date)

        # Формирование текста отчета
        text = f"📋 <b>Произвольный период</b>\n"
        text += f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>📈 ПРОДАЖИ</b>\n"
        text += f"Количество продаж: <b>{stats['total_sales']}</b> шт.\n"
        text += f"Общая выручка: <b>{stats['total_revenue']:,.2f}</b> ₽\n"
        text += f"Прибыль от продаж: <b>{stats['total_profit']:,.2f}</b> ₽\n\n"

        text += f"<b>💸 РАСХОДЫ</b>\n"
        text += f"Общие расходы: <b>{stats['total_expenses']:,.2f}</b> ₽\n\n"

        text += f"━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>💰 ЧИСТАЯ ПРИБЫЛЬ</b>\n"

        net_profit = stats['net_profit']
        if net_profit >= 0:
            text += f"<b>{net_profit:,.2f}</b> ₽ ✅"
        else:
            text += f"<b>{net_profit:,.2f}</b> ₽ ❌"

        # Детализация продаж
        if stats['sales']:
            text += f"\n\n<b>📦 ПРОДАННЫЕ ТОВАРЫ:</b>\n"
            for i, sale in enumerate(stats['sales'][:10], 1):
                date_str = datetime.fromisoformat(sale['sale_date']).strftime('%d.%m %H:%M')
                text += f"{i}. {sale['product_name']} - {sale['selling_price']:.2f}₽ ({date_str})\n"

            if len(stats['sales']) > 10:
                text += f"\n... и еще {len(stats['sales']) - 10} продаж"

        # Детализация расходов
        if stats['expenses']:
            text += f"\n\n<b>💸 РАСХОДЫ:</b>\n"
            for i, expense in enumerate(stats['expenses'][:5], 1):
                date_str = datetime.fromisoformat(expense['expense_date']).strftime('%d.%m %H:%M')
                text += f"{i}. {expense['comment'][:30]} - {expense['amount']:.2f}₽ ({date_str})\n"

            if len(stats['expenses']) > 5:
                text += f"\n... и еще {len(stats['expenses']) - 5} расходов"

        # Сохраняем период для экспорта
        period_str = f"custom:{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}"

        await callback.message.edit_text(
            text,
            reply_markup=get_stats_export_keyboard(period_str),
            parse_mode="HTML"
        )


# === РУЧНОЙ ВВОД - НАЧАЛЬНАЯ ДАТА ===

@router.message(CustomPeriodForm.waiting_for_start_date_manual)
async def process_start_date_manual(message: Message, state: FSMContext):
    """Обработка ручного ввода начальной даты"""
    try:
        start_date = datetime.strptime(message.text.strip(), '%d.%m.%Y')

        if start_date > datetime.now():
            await message.answer(
                "❌ Дата не может быть в будущем. Попробуйте снова:",
                parse_mode="HTML"
            )
            return

        await state.update_data(start_date=start_date)

        await message.answer(
            f"✅ Дата начала: <b>{start_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"⌨️ Теперь введите дату окончания периода\n"
            f"Формат: ДД.ММ.ГГГГ",
            parse_mode="HTML"
        )
        await state.set_state(CustomPeriodForm.waiting_for_end_date_manual)

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты!\n\n"
            "Используйте формат: ДД.ММ.ГГГГ\n"
            "Например: 01.01.2024",
            parse_mode="HTML"
        )


# === РУЧНОЙ ВВОД - КОНЕЧНАЯ ДАТА ===

@router.message(CustomPeriodForm.waiting_for_end_date_manual)
async def process_end_date_manual(message: Message, state: FSMContext):
    """Обработка ручного ввода конечной даты"""
    try:
        end_date = datetime.strptime(message.text.strip(), '%d.%m.%Y')

        data = await state.get_data()
        start_date = data['start_date']

        if end_date < start_date:
            await message.answer(
                "❌ Дата окончания не может быть раньше даты начала. Попробуйте снова:",
                parse_mode="HTML"
            )
            return

        if end_date > datetime.now():
            await message.answer(
                "❌ Дата не может быть в будущем. Попробуйте снова:",
                parse_mode="HTML"
            )
            return

        await state.update_data(end_date=end_date)
        await state.clear()

        # Получаем статистику за выбранный период
        stats = db.get_statistics_custom(start_date, end_date)

        # Формирование текста отчета (аналогично календарю)
        text = f"📋 <b>Произвольный период</b>\n"
        text += f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>📈 ПРОДАЖИ</b>\n"
        text += f"Количество продаж: <b>{stats['total_sales']}</b> шт.\n"
        text += f"Общая выручка: <b>{stats['total_revenue']:,.2f}</b> ₽\n"
        text += f"Прибыль от продаж: <b>{stats['total_profit']:,.2f}</b> ₽\n\n"

        text += f"<b>💸 РАСХОДЫ</b>\n"
        text += f"Общие расходы: <b>{stats['total_expenses']:,.2f}</b> ₽\n\n"

        text += f"━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>💰 ЧИСТАЯ ПРИБЫЛЬ</b>\n"

        net_profit = stats['net_profit']
        if net_profit >= 0:
            text += f"<b>{net_profit:,.2f}</b> ₽ ✅"
        else:
            text += f"<b>{net_profit:,.2f}</b> ₽ ❌"

        if stats['sales']:
            text += f"\n\n<b>📦 ПРОДАННЫЕ ТОВАРЫ:</b>\n"
            for i, sale in enumerate(stats['sales'][:10], 1):
                date_str = datetime.fromisoformat(sale['sale_date']).strftime('%d.%m %H:%M')
                text += f"{i}. {sale['product_name']} - {sale['selling_price']:.2f}₽ ({date_str})\n"

            if len(stats['sales']) > 10:
                text += f"\n... и еще {len(stats['sales']) - 10} продаж"

        if stats['expenses']:
            text += f"\n\n<b>💸 РАСХОДЫ:</b>\n"
            for i, expense in enumerate(stats['expenses'][:5], 1):
                date_str = datetime.fromisoformat(expense['expense_date']).strftime('%d.%m %H:%M')
                text += f"{i}. {expense['comment'][:30]} - {expense['amount']:.2f}₽ ({date_str})\n"

            if len(stats['expenses']) > 5:
                text += f"\n... и еще {len(stats['expenses']) - 5} расходов"

        period_str = f"custom:{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}"

        await message.answer(
            text,
            reply_markup=get_stats_export_keyboard(period_str),
            parse_mode="HTML"
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты!\n\n"
            "Используйте формат: ДД.ММ.ГГГГ\n"
            "Например: 31.12.2024",
            parse_mode="HTML"
        )


# === ЭКСПОРТ PDF ===

@router.callback_query(F.data.startswith("export_pdf:"))
async def export_pdf(callback: CallbackQuery):
    """Экспорт статистики в PDF"""
    await callback.answer("⏳ Генерация PDF...", show_alert=False)

    period_data = callback.data.split(":")[1:]

    if len(period_data) == 3 and period_data[0] == "custom":
        # Произвольный период
        start_date = datetime.strptime(period_data[1], '%Y-%m-%d')
        end_date = datetime.strptime(period_data[2], '%Y-%m-%d')
        stats = db.get_statistics_custom(start_date, end_date)
        filename = f"отчет_{start_date.strftime('%d%m%Y')}-{end_date.strftime('%d%m%Y')}.pdf"
    else:
        # Стандартный период
        period = period_data[0]
        stats = db.get_statistics(period)
        period_names = {
            'day': 'день',
            'month': 'месяц',
            'all': 'все_время'
        }
        filename = f"отчет_{period_names[period]}_{datetime.now().strftime('%d%m%Y')}.pdf"

    # Генерация PDF
    pdf_buffer = PDFGenerator.generate_statistics_report(stats)

    # Отправка файла
    pdf_file = BufferedInputFile(pdf_buffer.read(), filename=filename)

    await callback.message.answer_document(
        document=pdf_file,
        caption=f"📄 <b>Отчет о продажах</b>\n\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML"
    )

    await callback.answer("✅ PDF отчет готов!")