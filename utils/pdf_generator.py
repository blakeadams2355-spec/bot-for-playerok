"""
Генератор PDF отчетов
"""
import io
import os
from datetime import datetime
from typing import Dict
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# Регистрация шрифтов DejaVu для поддержки кириллицы
def register_fonts():
    """Регистрация шрифтов с поддержкой кириллицы"""
    try:
        # Пути к шрифтам DejaVu для разных ОС
        font_paths = {
            'regular': [
                # Windows - системные шрифты
                'C:\\Windows\\Fonts\\arial.ttf',
                'C:\\Windows\\Fonts\\calibri.ttf',
                # DejaVu в Windows
                'C:\\Windows\\Fonts\\DejaVuSans.ttf',
                # Linux
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                # MacOS
                '/Library/Fonts/Arial.ttf',
            ],
            'bold': [
                # Windows - системные шрифты
                'C:\\Windows\\Fonts\\arialbd.ttf',
                'C:\\Windows\\Fonts\\calibrib.ttf',
                # DejaVu в Windows
                'C:\\Windows\\Fonts\\DejaVuSans-Bold.ttf',
                # Linux
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
                # MacOS
                '/Library/Fonts/Arial Bold.ttf',
            ]
        }

        regular_font = None
        bold_font = None

        # Ищем обычный шрифт
        for path in font_paths['regular']:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('CustomFont', path))
                regular_font = path
                print(f"✓ Зарегистрирован шрифт: {path}")
                break

        # Ищем жирный шрифт
        for path in font_paths['bold']:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont('CustomFont-Bold', path))
                bold_font = path
                print(f"✓ Зарегистрирован жирный шрифт: {path}")
                break

        if regular_font and bold_font:
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily(
                'CustomFont',
                normal='CustomFont',
                bold='CustomFont-Bold',
                italic='CustomFont',
                boldItalic='CustomFont-Bold'
            )
            return True

        return False
    except Exception as e:
        print(f"⚠ Ошибка регистрации шрифтов: {e}")
        return False

# Регистрируем шрифты при импорте модуля
FONTS_REGISTERED = register_fonts()

class PDFGenerator:
    """Генератор PDF отчетов"""

    @staticmethod
    def generate_statistics_report(stats: Dict) -> io.BytesIO:
        """Генерация PDF отчета по статистике"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        elements = []

        # Определяем шрифт
        if FONTS_REGISTERED:
            font_name = 'CustomFont'
            font_name_bold = 'CustomFont-Bold'
        else:
            font_name = 'Helvetica'
            font_name_bold = 'Helvetica-Bold'
            print("⚠ Используются стандартные шрифты без кириллицы")

        # Стили
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name_bold,
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER,
            leading=24
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_name_bold,
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12,
            leading=18
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14
        )

        bold_style = ParagraphStyle(
            'CustomBold',
            parent=normal_style,
            fontName=font_name_bold
        )

        # Заголовок
        period_names = {
            'day': 'за сегодня',
            'month': 'за текущий месяц',
            'all': 'за всё время'
        }
        period_name = period_names.get(stats['period'], stats['period'])

        title_text = f"Отчет о продажах {period_name}"
        date_text = f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        title = Paragraph(title_text, title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))

        # Дата генерации
        date_para = Paragraph(date_text, normal_style)
        elements.append(date_para)
        elements.append(Spacer(1, 0.8*cm))

        # Общая статистика
        summary_heading = Paragraph("Общая статистика", heading_style)
        elements.append(summary_heading)

        summary_data = [
            [
                Paragraph('<b>Показатель</b>', bold_style),
                Paragraph('<b>Значение</b>', bold_style)
            ],
            [
                Paragraph('Количество продаж', normal_style),
                Paragraph(f"{stats['total_sales']} шт.", normal_style)
            ],
            [
                Paragraph('Общая выручка', normal_style),
                Paragraph(f"{stats['total_revenue']:,.2f} ₽", normal_style)
            ],
            [
                Paragraph('Прибыль от продаж', normal_style),
                Paragraph(f"{stats['total_profit']:,.2f} ₽", normal_style)
            ],
            [
                Paragraph('Расходы', normal_style),
                Paragraph(f"{stats['total_expenses']:,.2f} ₽", normal_style)
            ],
            [
                Paragraph('Чистая прибыль', normal_style),
                Paragraph(f"<b>{stats['net_profit']:,.2f} ₽</b>", bold_style)
            ],
        ]

        summary_table = Table(summary_data, colWidths=[10*cm, 6*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 1*cm))

        # Детализация продаж
        if stats['sales']:
            sales_heading = Paragraph("Детализация продаж", heading_style)
            elements.append(sales_heading)

            sales_data = [
                [
                    Paragraph('<b>№</b>', bold_style),
                    Paragraph('<b>Товар</b>', bold_style),
                    Paragraph('<b>Дата</b>', bold_style),
                    Paragraph('<b>Цена</b>', bold_style),
                    Paragraph('<b>Прибыль</b>', bold_style)
                ]
            ]

            for i, sale in enumerate(stats['sales'], 1):
                date_str = datetime.fromisoformat(sale['sale_date']).strftime('%d.%m.%Y %H:%M')
                product_name = sale['product_name'][:40]

                sales_data.append([
                    Paragraph(str(i), normal_style),
                    Paragraph(product_name, normal_style),
                    Paragraph(date_str, normal_style),
                    Paragraph(f"{sale['selling_price']:,.2f} ₽", normal_style),
                    Paragraph(f"{sale['profit']:,.2f} ₽", normal_style)
                ])

            sales_table = Table(sales_data, colWidths=[1.5*cm, 6*cm, 3.5*cm, 3*cm, 3*cm])
            sales_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ECC71')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))

            elements.append(sales_table)
            elements.append(Spacer(1, 1*cm))

        # Детализация расходов
        if stats['expenses']:
            expenses_heading = Paragraph("Детализация расходов", heading_style)
            elements.append(expenses_heading)

            expenses_data = [
                [
                    Paragraph('<b>№</b>', bold_style),
                    Paragraph('<b>Комментарий</b>', bold_style),
                    Paragraph('<b>Дата</b>', bold_style),
                    Paragraph('<b>Сумма</b>', bold_style)
                ]
            ]

            for i, expense in enumerate(stats['expenses'], 1):
                date_str = datetime.fromisoformat(expense['expense_date']).strftime('%d.%m.%Y %H:%M')
                comment = expense['comment'][:50]

                expenses_data.append([
                    Paragraph(str(i), normal_style),
                    Paragraph(comment, normal_style),
                    Paragraph(date_str, normal_style),
                    Paragraph(f"{expense['amount']:,.2f} ₽", normal_style)
                ])

            expenses_table = Table(expenses_data, colWidths=[1.5*cm, 8*cm, 4*cm, 3*cm])
            expenses_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))

            elements.append(expenses_table)

        # Генерация диаграммы
        if stats['total_profit'] > 0 or stats['total_expenses'] > 0:
            elements.append(PageBreak())

            chart_heading = Paragraph("Диаграмма доходов и расходов", heading_style)
            elements.append(chart_heading)
            elements.append(Spacer(1, 0.5*cm))

            chart_buffer = PDFGenerator._create_profit_chart(stats, FONTS_REGISTERED)
            if chart_buffer:
                from reportlab.platypus import Image
                img = Image(chart_buffer, width=15*cm, height=10*cm)
                elements.append(img)

        # Сборка PDF
        try:
            doc.build(elements)
            buffer.seek(0)
            return buffer
        except Exception as e:
            print(f"Ошибка при создании PDF: {e}")
            # Пробуем создать упрощенную версию без Paragraph
            return PDFGenerator._generate_simple_report(stats)

    @staticmethod
    def _generate_simple_report(stats: Dict) -> io.BytesIO:
        """Упрощенная версия отчета (на случай проблем со шрифтами)"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        # Простые данные без Paragraph
        period_names = {
            'day': 'za segodnya',
            'month': 'za mesyac',
            'all': 'za vse vremya'
        }

        data = [
            ['Otchet o prodazhah', period_names.get(stats['period'], stats['period'])],
            ['', ''],
            ['Pokazatel', 'Znachenie'],
            ['Kolichestvo prodazh', f"{stats['total_sales']} sht."],
            ['Vyruchka', f"{stats['total_revenue']:,.2f} rub."],
            ['Pribyl', f"{stats['total_profit']:,.2f} rub."],
            ['Rashody', f"{stats['total_expenses']:,.2f} rub."],
            ['Chistaya pribyl', f"{stats['net_profit']:,.2f} rub."],
        ]

        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 2), (-1, 2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _create_profit_chart(stats: Dict, fonts_available: bool = True) -> io.BytesIO:
        """Создание диаграммы прибыли"""
        try:
            # Настройка шрифта для matplotlib
            if fonts_available:
                try:
                    # Попытка использовать системные шрифты Windows с кириллицей
                    if os.name == 'nt':  # Windows
                        plt.rcParams['font.family'] = 'Arial'
                    else:
                        plt.rcParams['font.family'] = 'DejaVu Sans'
                except:
                    fonts_available = False

            fig, ax = plt.subplots(figsize=(10, 6))

            if fonts_available:
                categories = ['Прибыль от\nпродаж', 'Расходы', 'Чистая\nприбыль']
                title = 'Финансовые показатели'
                ylabel = 'Сумма, ₽'
            else:
                categories = ['Sales\nprofit', 'Expenses', 'Net\nprofit']
                title = 'Financial indicators'
                ylabel = 'Amount, RUB'

            values = [
                stats['total_profit'],
                stats['total_expenses'],
                stats['net_profit']
            ]
            colors_list = ['#2ECC71', '#E74C3C', '#3498DB']

            bars = ax.bar(categories, values, color=colors_list, alpha=0.85, edgecolor='black', linewidth=1.5)

            # Добавление значений на столбцы
            for bar in bars:
                height = bar.get_height()
                label = f'{height:,.0f}'
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       label,
                       ha='center', va='bottom', fontsize=12, fontweight='bold')

            ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
            ax.set_title(title, fontsize=15, fontweight='bold', pad=20)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            # Форматирование оси Y
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

            plt.tight_layout()

            # Сохранение в буфер
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            buffer.seek(0)
            plt.close()

            return buffer
        except Exception as e:
            print(f"Ошибка создания диаграммы: {e}")
            return None