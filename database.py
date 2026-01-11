"""
Работа с базой данных SQLite
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Создание подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица настроек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            # Устанавливаем комиссию по умолчанию
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value)
                VALUES ('commission', '15.0')
            ''')

            # Таблица категорий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица товаров (с поставщиком)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    photo_id TEXT,
                    purchase_price REAL NOT NULL,
                    selling_price REAL NOT NULL,
                    supplier_name TEXT,
                    supplier_link TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            ''')

            # Проверяем и добавляем новые столбцы если их нет
            cursor.execute("PRAGMA table_info(products)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'supplier_name' not in columns:
                cursor.execute('ALTER TABLE products ADD COLUMN supplier_name TEXT')
            if 'supplier_link' not in columns:
                cursor.execute('ALTER TABLE products ADD COLUMN supplier_link TEXT')

            # Таблица продаж
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    purchase_price REAL NOT NULL,
                    selling_price REAL NOT NULL,
                    commission_percent REAL NOT NULL,
                    profit REAL NOT NULL,
                    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_cancelled INTEGER DEFAULT 0,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            ''')

            # Проверяем и добавляем столбец отмены
            cursor.execute("PRAGMA table_info(sales)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'is_cancelled' not in columns:
                cursor.execute('ALTER TABLE sales ADD COLUMN is_cancelled INTEGER DEFAULT 0')

            # Таблица расходов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    comment TEXT NOT NULL,
                    expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.info("База данных инициализирована")

    # === НАСТРОЙКИ ===

    def get_commission(self) -> float:
        """Получить процент комиссии"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', ('commission',))
            result = cursor.fetchone()
            return float(result['value']) if result else 15.0

    def set_commission(self, commission: float):
        """Установить процент комиссии"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('commission', ?)
            ''', (str(commission),))
            conn.commit()

    # === КАТЕГОРИИ ===

    def add_category(self, name: str) -> int:
        """Добавить категорию"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
            conn.commit()
            return cursor.lastrowid

    def get_categories(self) -> List[Dict]:
        """Получить все категории"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM categories ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]

    def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        """Получить категорию по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def category_exists(self, name: str) -> bool:
        """Проверить существование категории"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
            return cursor.fetchone() is not None

    # === ТОВАРЫ ===

    def add_product(self, category_id: int, name: str, photo_id: str,
                    purchase_price: float, selling_price: float,
                    supplier_name: str = None, supplier_link: str = None) -> int:
        """Добавить товар"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products 
                (category_id, name, photo_id, purchase_price, selling_price, supplier_name, supplier_link)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (category_id, name, photo_id, purchase_price, selling_price, supplier_name, supplier_link))
            conn.commit()
            return cursor.lastrowid

    def get_products_by_category(self, category_id: int) -> List[Dict]:
        """Получить товары по категории"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, c.name as category_name
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.category_id = ?
                ORDER BY p.name
            ''', (category_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Получить товар по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, c.name as category_name
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?
            ''', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_product_prices(self, product_id: int, purchase_price: float = None,
                             selling_price: float = None):
        """Обновить цены товара"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if purchase_price is not None and selling_price is not None:
                cursor.execute('''
                    UPDATE products 
                    SET purchase_price = ?, selling_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (purchase_price, selling_price, product_id))
            elif purchase_price is not None:
                cursor.execute('''
                    UPDATE products 
                    SET purchase_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (purchase_price, product_id))
            elif selling_price is not None:
                cursor.execute('''
                    UPDATE products 
                    SET selling_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (selling_price, product_id))
            conn.commit()

    def update_product_info(self, product_id: int, name: str = None, photo_id: str = None):
        """Обновить информацию о товаре"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if name and photo_id:
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, photo_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, photo_id, product_id))
            elif name:
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, product_id))
            elif photo_id:
                cursor.execute('''
                    UPDATE products 
                    SET photo_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (photo_id, product_id))
            conn.commit()

    def update_product_supplier(self, product_id: int, supplier_name: str = None, supplier_link: str = None):
        """Обновить информацию о поставщике"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET supplier_name = ?, supplier_link = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (supplier_name, supplier_link, product_id))
            conn.commit()

    def delete_product(self, product_id: int):
        """Удалить товар"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            conn.commit()

    # === ПРОДАЖИ ===

    def add_sale(self, product_id: int) -> Tuple[int, float]:
        """
        Добавить продажу
        Возвращает (sale_id, profit)
        """
        product = self.get_product_by_id(product_id)
        commission = self.get_commission()

        # Формула: Прибыль = ЦенаПродажи - ЦенаЗакупки - (ЦенаПродажи * %Комиссии)
        profit = product['selling_price'] - product['purchase_price'] - \
                 (product['selling_price'] * commission / 100)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sales 
                (product_id, product_name, purchase_price, selling_price, 
                 commission_percent, profit, is_cancelled)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            ''', (product_id, product['name'], product['purchase_price'],
                  product['selling_price'], commission, profit))
            conn.commit()
            return cursor.lastrowid, profit

    def cancel_sale(self, sale_id: int) -> bool:
        """
        Отменить продажу
        Возвращает True если успешно, False если продажа не найдена или уже отменена
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем существование продажи
            cursor.execute('SELECT is_cancelled FROM sales WHERE id = ?', (sale_id,))
            result = cursor.fetchone()

            if not result:
                return False

            if result['is_cancelled'] == 1:
                return False

            # Отмечаем продажу как отменённую
            cursor.execute('''
                UPDATE sales 
                SET is_cancelled = 1
                WHERE id = ?
            ''', (sale_id,))
            conn.commit()
            return True

    def get_sale_by_id(self, sale_id: int) -> Optional[Dict]:
        """Получить продажу по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sales WHERE id = ?', (sale_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_sales(self, period: str = 'all') -> List[Dict]:
        """
        Получить продажи за период (только активные, не отменённые)
        period: 'day', 'month', 'all'
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if period == 'day':
                query = '''
                    SELECT * FROM sales 
                    WHERE DATE(sale_date) = DATE('now') AND is_cancelled = 0
                    ORDER BY sale_date DESC
                '''
            elif period == 'month':
                query = '''
                    SELECT * FROM sales 
                    WHERE strftime('%Y-%m', sale_date) = strftime('%Y-%m', 'now') AND is_cancelled = 0
                    ORDER BY sale_date DESC
                '''
            else:  # all
                query = 'SELECT * FROM sales WHERE is_cancelled = 0 ORDER BY sale_date DESC'

            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    # === РАСХОДЫ ===

    def add_expense(self, amount: float, comment: str) -> int:
        """Добавить расход"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO expenses (amount, comment)
                VALUES (?, ?)
            ''', (amount, comment))
            conn.commit()
            return cursor.lastrowid

    def get_expenses(self, period: str = 'all') -> List[Dict]:
        """
        Получить расходы за период
        period: 'day', 'month', 'all'
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if period == 'day':
                query = '''
                    SELECT * FROM expenses 
                    WHERE DATE(expense_date) = DATE('now')
                    ORDER BY expense_date DESC
                '''
            elif period == 'month':
                query = '''
                    SELECT * FROM expenses 
                    WHERE strftime('%Y-%m', expense_date) = strftime('%Y-%m', 'now')
                    ORDER BY expense_date DESC
                '''
            else:  # all
                query = 'SELECT * FROM expenses ORDER BY expense_date DESC'

            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    # === СТАТИСТИКА ===

    def get_statistics(self, period: str = 'all') -> Dict:
        """Получить статистику за период"""
        sales = self.get_sales(period)
        expenses = self.get_expenses(period)

        total_sales = len(sales)
        total_revenue = sum(s['selling_price'] for s in sales)
        total_profit = sum(s['profit'] for s in sales)
        total_expenses = sum(e['amount'] for e in expenses)
        net_profit = total_profit - total_expenses

        return {
            'period': period,
            'total_sales': total_sales,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'sales': sales,
            'expenses': expenses
        }

    def get_statistics_custom(self, start_date: datetime, end_date: datetime) -> Dict:
        """Получить статистику за произвольный период"""
        # Преобразуем datetime в строки для SQL
        start_str = start_date.strftime('%Y-%m-%d 00:00:00')
        end_str = end_date.strftime('%Y-%m-%d 23:59:59')

        # Получаем продажи (только не отменённые)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sales 
                WHERE sale_date BETWEEN ? AND ? AND is_cancelled = 0
                ORDER BY sale_date DESC
            ''', (start_str, end_str))
            sales = [dict(row) for row in cursor.fetchall()]

        # Получаем расходы
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM expenses 
                WHERE expense_date BETWEEN ? AND ?
                ORDER BY expense_date DESC
            ''', (start_str, end_str))
            expenses = [dict(row) for row in cursor.fetchall()]

        total_sales = len(sales)
        total_revenue = sum(s['selling_price'] for s in sales)
        total_profit = sum(s['profit'] for s in sales)
        total_expenses = sum(e['amount'] for e in expenses)
        net_profit = total_profit - total_expenses

        return {
            'period': 'custom',
            'start_date': start_date,
            'end_date': end_date,
            'total_sales': total_sales,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'sales': sales,
            'expenses': expenses
        }