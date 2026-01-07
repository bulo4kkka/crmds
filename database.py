import sqlite3
import traceback
from datetime import datetime, timedelta


class Database:
    def __init__(self, db_name='autoservice.db'):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """Инициализация базы данных"""
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.create_tables()
            print(f"✅ База данных {self.db_name} инициализирована")
        except Exception as e:
            print(f"❌ Ошибка инициализации БД: {e}")
            traceback.print_exc()
            raise

    def create_tables(self):
        """Создание всех таблиц"""
        cursor = self.conn.cursor()

        # Включаем поддержку внешних ключей
        cursor.execute('PRAGMA foreign_keys = ON')

        # Клиенты
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS clients
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           full_name
                           TEXT
                           NOT
                           NULL,
                           phone
                           TEXT
                           NOT
                           NULL
                           UNIQUE,
                           car_model
                           TEXT
                           NOT
                           NULL,
                           car_number
                           TEXT,
                           car_year
                           INTEGER,
                           vin
                           TEXT,
                           notes
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Заказ-наряды
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS work_orders
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           client_id
                           INTEGER
                           NOT
                           NULL,
                           order_number
                           TEXT
                           UNIQUE,
                           description
                           TEXT
                           NOT
                           NULL,
                           status
                           TEXT
                           DEFAULT
                           'new',
                           total_amount
                           REAL
                           DEFAULT
                           0,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           completed_at
                           TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           client_id
                       ) REFERENCES clients
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        # Работы в заказ-наряде
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS order_works
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           order_id
                           INTEGER
                           NOT
                           NULL,
                           work_name
                           TEXT
                           NOT
                           NULL,
                           quantity
                           INTEGER
                           DEFAULT
                           1,
                           price_per_unit
                           REAL
                           DEFAULT
                           0,
                           total_price
                           REAL
                           DEFAULT
                           0,
                           FOREIGN
                           KEY
                       (
                           order_id
                       ) REFERENCES work_orders
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        # Расходы в заказ-наряде
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS order_expenses
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           order_id
                           INTEGER
                           NOT
                           NULL,
                           expense_name
                           TEXT
                           NOT
                           NULL,
                           expense_type
                           TEXT
                           DEFAULT
                           'material',
                           quantity
                           INTEGER
                           DEFAULT
                           1,
                           cost_per_unit
                           REAL
                           DEFAULT
                           0,
                           total_cost
                           REAL
                           DEFAULT
                           0,
                           notes
                           TEXT,
                           FOREIGN
                           KEY
                       (
                           order_id
                       ) REFERENCES work_orders
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        # Задачи
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS tasks
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           title
                           TEXT
                           NOT
                           NULL,
                           description
                           TEXT,
                           priority
                           TEXT
                           DEFAULT
                           'medium',
                           status
                           TEXT
                           DEFAULT
                           'pending',
                           assigned_to
                           TEXT,
                           due_date
                           TIMESTAMP,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           completed_at
                           TIMESTAMP
                       )
                       ''')

        # Касса (доходы и расходы)
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS cash_flow
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           transaction_type
                           TEXT
                           NOT
                           NULL, -- 'income' или 'expense'
                           category
                           TEXT
                           NOT
                           NULL,
                           amount
                           REAL
                           NOT
                           NULL,
                           description
                           TEXT,
                           order_id
                           INTEGER,
                           date
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           order_id
                       ) REFERENCES work_orders
                       (
                           id
                       ) ON DELETE SET NULL
                           )
                       ''')

        # Настройки
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS settings
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           key
                           TEXT
                           NOT
                           NULL
                           UNIQUE,
                           value
                           TEXT,
                           category
                           TEXT
                           DEFAULT
                           'general',
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           updated_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON work_orders(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cashflow_date ON cash_flow(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cashflow_type ON cash_flow(transaction_type)')

        # Добавляем начальные настройки
        self._init_settings()

        self.conn.commit()
        print("✅ Все таблицы созданы/проверены")

    def _init_settings(self):
        """Инициализация настроек по умолчанию"""
        cursor = self.conn.cursor()

        default_settings = [
            ('dashboard_period', 'month', 'dashboard'),
            ('dashboard_show_expenses', 'true', 'dashboard'),
            ('dashboard_quick_actions', 'new_client,new_order,new_task,cash_view', 'dashboard'),
            ('tax_rate', '20', 'finance'),
            ('currency', '₽', 'general'),
            ('company_name', 'Автосервис', 'general')
        ]

        for key, value, category in default_settings:
            cursor.execute('''
                           INSERT
                           OR IGNORE INTO settings (key, value, category)
                VALUES (?, ?, ?)
                           ''', (key, value, category))

    # ========== НАСТРОЙКИ ==========

    def get_setting(self, key, default=None):
        """Получение настройки"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result else default

    def update_setting(self, key, value):
        """Обновление настройки"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value))
        self.conn.commit()
        return True

    def get_all_settings(self, category=None):
        """Получение всех настроек"""
        cursor = self.conn.cursor()
        if category:
            cursor.execute('SELECT * FROM settings WHERE category = ? ORDER BY key', (category,))
        else:
            cursor.execute('SELECT * FROM settings ORDER BY category, key')

        # Создаем структурированный словарь
        settings_dict = {}
        for row in cursor.fetchall():
            cat = row['category']
            if cat not in settings_dict:
                settings_dict[cat] = []
            settings_dict[cat].append(dict(row))

        return settings_dict

    # ========== КЛИЕНТЫ ==========

    def add_client(self, full_name, phone, car_model='', car_number='', car_year=None, vin='', notes=''):
        """Добавление нового клиента"""
        cursor = self.conn.cursor()
        try:
            if car_year:
                try:
                    car_year = int(car_year)
                except:
                    car_year = None

            cursor.execute('''
                           INSERT INTO clients (full_name, phone, car_model, car_number, car_year, vin, notes)
                           VALUES (?, ?, ?, ?, ?, ?, ?)
                           ''', (full_name, phone, car_model, car_number, car_year, vin, notes))

            self.conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            if 'UNIQUE constraint failed' in str(e):
                raise ValueError(f"Клиент с телефоном {phone} уже существует")
            raise

    def get_clients(self, search_term=None):
        """Получение всех клиентов с возможностью поиска"""
        cursor = self.conn.cursor()
        if search_term:
            search_pattern = f'%{search_term}%'
            cursor.execute('''
                           SELECT *
                           FROM clients
                           WHERE full_name LIKE ?
                              OR phone LIKE ?
                              OR car_model LIKE ?
                              OR car_number LIKE ?
                           ORDER BY created_at DESC
                           ''', (search_pattern, search_pattern, search_pattern, search_pattern))
        else:
            cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
        return cursor.fetchall()

    def get_client(self, client_id):
        """Получение клиента по ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        return cursor.fetchone()

    def update_client(self, client_id, **kwargs):
        """Обновление данных клиента"""
        cursor = self.conn.cursor()
        if not kwargs:
            return False

        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(client_id)

        cursor.execute(f'UPDATE clients SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_client(self, client_id):
        """Удаление клиента"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ========== ЗАКАЗ-НАРЯДЫ ==========

    def add_work_order(self, client_id, description, order_number=None, total_amount=0):
        """Добавление нового заказ-наряда - БЕЗ автоматического добавления в кассу"""
        cursor = self.conn.cursor()
        try:
            if not order_number:
                # Генерация номера заказа
                date_str = datetime.now().strftime("%y%m%d")
                cursor.execute('SELECT COUNT(*) FROM work_orders WHERE order_number LIKE ?', (f'{date_str}%',))
                count = cursor.fetchone()[0] + 1
                order_number = f"{date_str}-{count:03d}"

            # Вставляем заказ-наряд БЕЗ вызова add_cash_flow
            cursor.execute('''
                           INSERT INTO work_orders (client_id, order_number, description, total_amount)
                           VALUES (?, ?, ?, ?)
                           ''', (client_id, order_number, description, total_amount))

            order_id = cursor.lastrowid
            self.conn.commit()

            print(f"✅ Заказ-наряд создан: ID={order_id}, номер={order_number}, сумма={total_amount}")
            print(f"✅ НЕ добавляем автоматически в кассу - это будет сделано при завершении заказа")

            return order_id

        except Exception as e:
            self.conn.rollback()
            raise

    def complete_work_order(self, order_id):
        """Завершение заказ-наряда и добавление дохода в кассу"""
        cursor = self.conn.cursor()
        try:
            # Получаем информацию о заказе
            cursor.execute('SELECT order_number, total_amount FROM work_orders WHERE id = ?', (order_id,))
            order = cursor.fetchone()

            if not order:
                raise ValueError(f"Заказ-наряд #{order_id} не найден")

            order_number = order['order_number']
            total_amount = order['total_amount']

            # Обновляем статус
            cursor.execute('''
                           UPDATE work_orders
                           SET status       = 'completed',
                               completed_at = CURRENT_TIMESTAMP
                           WHERE id = ?
                           ''', (order_id,))

            # Добавляем доход в кассу только если есть сумма
            if total_amount > 0:
                self.add_cash_flow(
                    transaction_type='income',
                    category='order_income',
                    amount=total_amount,
                    description=f'Доход от заказа {order_number}',
                    order_id=order_id
                )
                print(f"✅ Добавлен доход в кассу для заказа #{order_number}: {total_amount} ₽")

            self.conn.commit()
            return True

        except Exception as e:
            self.conn.rollback()
            raise

    def add_order_work(self, order_id, work_name, quantity=1, price_per_unit=0):
        """Добавление работы в заказ-наряд"""
        cursor = self.conn.cursor()
        total_price = quantity * price_per_unit

        cursor.execute('''
                       INSERT INTO order_works (order_id, work_name, quantity, price_per_unit, total_price)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (order_id, work_name, quantity, price_per_unit, total_price))

        # Обновляем общую сумму заказа
        cursor.execute('''
                       UPDATE work_orders
                       SET total_amount = total_amount + ?
                       WHERE id = ?
                       ''', (total_price, order_id))

        self.conn.commit()
        return cursor.lastrowid

    def add_order_expense(self, order_id, expense_name, expense_type='material', quantity=1, cost_per_unit=0, notes=''):
        """Добавление расхода в заказ-наряд"""
        cursor = self.conn.cursor()
        total_cost = quantity * cost_per_unit

        print(f"📊 Добавление расхода для заказа #{order_id}: {expense_name}, сумма={total_cost}")

        cursor.execute('''
                       INSERT INTO order_expenses (order_id, expense_name, expense_type, quantity, cost_per_unit,
                                                   total_cost, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ''', (order_id, expense_name, expense_type, quantity, cost_per_unit, total_cost, notes))

        # НЕ добавляем расход в кассу автоматически!
        # Расходы будут учитываться отдельно через модуль кассы

        self.conn.commit()
        return cursor.lastrowid

    def get_work_orders(self, search_term=None):
        """Получение всех заказ-нарядов"""
        cursor = self.conn.cursor()
        if search_term:
            search_pattern = f'%{search_term}%'
            cursor.execute('''
                           SELECT wo.*, c.full_name, c.phone, c.car_model, c.car_number
                           FROM work_orders wo
                                    JOIN clients c ON wo.client_id = c.id
                           WHERE wo.order_number LIKE ?
                              OR c.full_name LIKE ?
                              OR c.phone LIKE ?
                           ORDER BY wo.created_at DESC
                           ''', (search_pattern, search_pattern, search_pattern))
        else:
            cursor.execute('''
                           SELECT wo.*, c.full_name, c.phone, c.car_model, c.car_number
                           FROM work_orders wo
                                    JOIN clients c ON wo.client_id = c.id
                           ORDER BY wo.created_at DESC
                           ''')
        return cursor.fetchall()

    def get_work_order(self, order_id):
        """Получение заказ-наряда по ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
                       SELECT wo.*, c.full_name, c.phone, c.car_model, c.car_number, c.car_year, c.vin
                       FROM work_orders wo
                                JOIN clients c ON wo.client_id = c.id
                       WHERE wo.id = ?
                       ''', (order_id,))
        return cursor.fetchone()

    def get_order_works(self, order_id):
        """Получение работ заказ-наряда"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM order_works WHERE order_id = ? ORDER BY id', (order_id,))
        return cursor.fetchall()

    def get_order_expenses(self, order_id):
        """Получение расходов заказ-наряда"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM order_expenses WHERE order_id = ? ORDER BY id', (order_id,))
        return cursor.fetchall()

    def update_work_order_status(self, order_id, status):
        """Обновление статуса заказ-наряда"""
        cursor = self.conn.cursor()
        if status == 'completed':
            cursor.execute('''
                           UPDATE work_orders
                           SET status       = ?,
                               completed_at = CURRENT_TIMESTAMP
                           WHERE id = ?
                           ''', (status, order_id))
        else:
            cursor.execute('''
                           UPDATE work_orders
                           SET status       = ?,
                               completed_at = NULL
                           WHERE id = ?
                           ''', (status, order_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_work_order(self, order_id):
        """Удаление заказ-наряда"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM work_orders WHERE id = ?', (order_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ========== ЗАДАЧИ ==========

    def add_task(self, title, description='', priority='medium', assigned_to='', due_date=None):
        """Добавление новой задачи"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                           INSERT INTO tasks (title, description, priority, assigned_to, due_date)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (title, description, priority, assigned_to, due_date))

            self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
            self.conn.rollback()
            raise

    def get_tasks(self, status=None):
        """Получение задач"""
        cursor = self.conn.cursor()
        if status:
            cursor.execute('''
                           SELECT *
                           FROM tasks
                           WHERE status = ?
                           ORDER BY CASE priority
                                        WHEN 'high' THEN 1
                                        WHEN 'medium' THEN 2
                                        WHEN 'low' THEN 3
                                        END,
                                    due_date ASC,
                                    created_at DESC
                           ''', (status,))
        else:
            cursor.execute('''
                           SELECT *
                           FROM tasks
                           ORDER BY CASE priority
                                        WHEN 'high' THEN 1
                                        WHEN 'medium' THEN 2
                                        WHEN 'low' THEN 3
                                        END,
                                    due_date ASC,
                                    created_at DESC
                           ''')
        return cursor.fetchall()

    def get_task(self, task_id):
        """Получение задачи по ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        return cursor.fetchone()

    def update_task(self, task_id, **kwargs):
        """Обновление задачи"""
        cursor = self.conn.cursor()
        if not kwargs:
            return False

        set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(task_id)

        cursor.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_task(self, task_id):
        """Удаление задачи"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ========== КАССА ==========

    def add_cash_flow(self, transaction_type, category, amount, description='', order_id=None):
        """Добавление операции в кассу"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                           INSERT INTO cash_flow (transaction_type, category, amount, description, order_id)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (transaction_type, category, amount, description, order_id))

            self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
            self.conn.rollback()
            raise

    def get_cash_flow(self, start_date=None, end_date=None, transaction_type=None):
        """Получение операций кассы за период"""
        cursor = self.conn.cursor()

        query = 'SELECT * FROM cash_flow WHERE 1=1'
        params = []

        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)

        if transaction_type:
            query += ' AND transaction_type = ?'
            params.append(transaction_type)

        query += ' ORDER BY date DESC'
        cursor.execute(query, params)
        return cursor.fetchall()

    def get_financial_stats(self, period='month'):
        """Получение финансовой статистики"""
        cursor = self.conn.cursor()

        # Определяем период
        end_date = datetime.now()
        if period == 'day':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=end_date.weekday())
        elif period == 'month':
            start_date = end_date.replace(day=1)
        elif period == 'year':
            start_date = end_date.replace(month=1, day=1)
        else:
            start_date = end_date - timedelta(days=30)  # по умолчанию 30 дней

        # Конвертируем в строки для SQL
        start_date_str = start_date.strftime('%Y-%m-%d 00:00:00')
        end_date_str = end_date.strftime('%Y-%m-%d 23:59:59')

        stats = {
            'period': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }

        print(f"📊 SQL запрос: start={start_date_str}, end={end_date_str}")

        # Доходы
        cursor.execute('''
                       SELECT COALESCE(SUM(amount), 0) as total_income
                       FROM cash_flow
                       WHERE transaction_type = 'income'
                         AND date >= ?
                         AND date <= ?
                       ''', (start_date_str, end_date_str))
        result = cursor.fetchone()
        stats['total_income'] = float(result[0]) if result and result[0] else 0.0

        # Расходы
        cursor.execute('''
                       SELECT COALESCE(SUM(amount), 0) as total_expenses
                       FROM cash_flow
                       WHERE transaction_type = 'expense'
                         AND date >= ?
                         AND date <= ?
                       ''', (start_date_str, end_date_str))
        result = cursor.fetchone()
        stats['total_expenses'] = float(result[0]) if result and result[0] else 0.0

        # Чистая прибыль
        stats['net_profit'] = stats['total_income'] - stats['total_expenses']

        # Доходы по категориям
        cursor.execute('''
                       SELECT category, COALESCE(SUM(amount), 0) as amount
                       FROM cash_flow
                       WHERE transaction_type = 'income'
                         AND date >= ?
                         AND date <= ?
                       GROUP BY category
                       ''', (start_date_str, end_date_str))

        income_by_category = []
        for row in cursor.fetchall():
            income_by_category.append({
                'category': row[0],
                'amount': float(row[1]) if row[1] else 0.0
            })
        stats['income_by_category'] = income_by_category

        # Расходы по категориям
        cursor.execute('''
                       SELECT category, COALESCE(SUM(amount), 0) as amount
                       FROM cash_flow
                       WHERE transaction_type = 'expense'
                         AND date >= ?
                         AND date <= ?
                       GROUP BY category
                       ''', (start_date_str, end_date_str))

        expenses_by_category = []
        for row in cursor.fetchall():
            expenses_by_category.append({
                'category': row[0],
                'amount': float(row[1]) if row[1] else 0.0
            })
        stats['expenses_by_category'] = expenses_by_category

        print(f"📊 Итоговая статистика: доходы={stats['total_income']}, расходы={stats['total_expenses']}")

        return stats

    def get_total_balance(self):
        """Получение общего баланса"""
        cursor = self.conn.cursor()
        cursor.execute('''
                       SELECT COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END),
                                       0)                                                                     as total_income,
                              COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END),
                                       0)                                                                     as total_expenses
                       FROM cash_flow
                       ''')
        result = cursor.fetchone()
        total_income = result[0] or 0
        total_expenses = result[1] or 0
        return total_income - total_expenses

    # ========== СТАТИСТИКА ==========

    def get_stats(self):
        """Получение общей статистики"""
        cursor = self.conn.cursor()

        stats = {}

        # Клиенты
        cursor.execute('SELECT COUNT(*) FROM clients')
        stats['total_clients'] = cursor.fetchone()[0]

        # Заказ-наряды
        cursor.execute('SELECT COUNT(*) FROM work_orders')
        stats['total_orders'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM work_orders WHERE status = "new"')
        stats['new_orders'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM work_orders WHERE status = "in_progress"')
        stats['in_progress_orders'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM work_orders WHERE status = "completed"')
        stats['completed_orders'] = cursor.fetchone()[0]

        # Общая выручка
        cursor.execute('SELECT COALESCE(SUM(total_amount), 0) FROM work_orders WHERE status = "completed"')
        stats['total_revenue'] = cursor.fetchone()[0] or 0

        # Задачи
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "pending"')
        stats['pending_tasks'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "in_progress"')
        stats['in_progress_tasks'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"')
        stats['completed_tasks'] = cursor.fetchone()[0]

        # Баланс
        stats['total_balance'] = self.get_total_balance()

        return stats

    def close(self):
        """Закрытие соединения"""
        if hasattr(self, 'conn'):
            self.conn.close()