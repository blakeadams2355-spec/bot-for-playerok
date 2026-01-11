"""
Обработчики для статистики и отчетов
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, BufferedInputFile
from keyboards.inline import get_statistics_menu, get_stats_export_keyboard, get_main_menu
from database import Database
from config import DATABASE_PATH
from utils.pdf_generator import PDFGenerator
from datetime import datetime

router = Router()
db = Database(DATABASE_PATH)


@router.callback_query(F.data == "statistics_menu")
async def show_statistics_menu(callback: CallbackQuery):
    """Показать меню статистики"""
    await callback.message.edit_text(
        "📊 <b>Статистика и отчеты</b>\n\n"
        "Выберите период для просмотра:",
        reply_markup=get_statistics_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stats:"))
async def show_statistics(callback: CallbackQuery):
    """Показать статистику за период"""
    period = callback.data.split(":")[1]
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
        for i, sale in enumerate(stats['sales'][:10], 1):  # Показываем последние 10
            date_str = datetime.fromisoformat(sale['sale_date']).strftime('%d.%m %H:%M')
            text += f"{i}. {sale['product_name']} - {sale['selling_price']:.2f}₽ ({date_str})\n"

        if len(stats['sales']) > 10:
            text += f"\n... и еще {len(stats['sales']) - 10} продаж"

    # Детализация расходов
    if stats['expenses']:
        text += f"\n\n<b>💸 РАСХОДЫ:</b>\n"
        for i, expense in enumerate(stats['expenses'][:5], 1):  # Показываем последние 5
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


@router.callback_query(F.data.startswith("export_pdf:"))
async def export_pdf(callback: CallbackQuery):
    """Экспорт статистики в PDF"""
    await callback.answer("⏳ Генерация PDF...", show_alert=False)

    period = callback.data.split(":")[1]
    stats = db.get_statistics(period)

    # Генерация PDF
    pdf_buffer = PDFGenerator.generate_statistics_report(stats)

    period_names = {
        'day': 'день',
        'month': 'месяц',
        'all': 'все_время'
    }

    filename = f"отчет_{period_names[period]}_{datetime.now().strftime('%d%m%Y')}.pdf"

    # Отправка файла
    pdf_file = BufferedInputFile(pdf_buffer.read(), filename=filename)

    await callback.message.answer_document(
        document=pdf_file,
        caption=f"📄 <b>Отчет о продажах</b>\n\n"
                f"Период: {period_names[period]}\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML"
    )

    await callback.answer("✅ PDF отчет готов!")