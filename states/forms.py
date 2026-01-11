"""
FSM состояния для форм
"""
from aiogram.fsm.state import State, StatesGroup


class ProductForm(StatesGroup):
    """Форма добавления товара"""
    waiting_for_photo = State()
    waiting_for_category = State()
    waiting_for_new_category = State()
    waiting_for_name = State()
    waiting_for_purchase_price = State()
    waiting_for_selling_price = State()


class EditProductForm(StatesGroup):
    """Форма редактирования товара"""
    waiting_for_choice = State()
    waiting_for_purchase_price = State()
    waiting_for_selling_price = State()
    waiting_for_photo = State()
    waiting_for_name = State()


class ExpenseForm(StatesGroup):
    """Форма добавления расхода"""
    waiting_for_amount = State()
    waiting_for_comment = State()


class CommissionForm(StatesGroup):
    """Форма изменения комиссии"""
    waiting_for_commission = State()


class CalculatorForm(StatesGroup):
    """Форма калькулятора прибыли"""
    waiting_for_purchase_price = State()
    waiting_for_selling_price = State()


class CustomPeriodForm(StatesGroup):
    """Форма выбора произвольного периода"""
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_start_date_manual = State()
    waiting_for_end_date_manual = State()

class ProductForm(StatesGroup):
    """Форма добавления товара"""
    waiting_for_photo = State()
    waiting_for_category = State()
    waiting_for_new_category = State()
    waiting_for_name = State()
    waiting_for_purchase_price = State()
    waiting_for_selling_price = State()
    waiting_for_supplier = State()  # Новое состояние