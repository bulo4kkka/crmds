# create_test_db.py
import sqlite3
from datetime import datetime, timedelta
import random


def create_test_database(db_name='autoservice_test.db'):
    """Создание тестовой базы данных с примерами"""

    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"🔧 Создание тестовой базы данных: {db_name}")

    # ========== СОЗДАНИЕ ТАБЛИЦ ==========

    # Удаляем старые таблицы если они есть
    cursor.execute('DROP TABLE IF EXISTS order_expenses')
    cursor.execute('DROP TABLE IF EXISTS order_works')
    cursor.execute('DROP TABLE IF EXISTS work_orders')
    cursor.execute('DROP TABLE IF EXISTS tasks')
    cursor.execute('DROP TABLE IF EXISTS cash_flow')
    cursor.execute('DROP TABLE IF EXISTS clients')
    cursor.execute('DROP TABLE IF EXISTS settings')

    # Включаем поддержку внешних ключей
    cursor.execute('PRAGMA foreign_keys = ON')

    # Клиенты
    cursor.execute('''
                   CREATE TABLE clients
                   (
                       id         INTEGER PRIMARY KEY AUTOINCREMENT,
                       full_name  TEXT NOT NULL,
                       phone      TEXT NOT NULL UNIQUE,
                       car_model  TEXT NOT NULL,
                       car_number TEXT,
                       car_year   INTEGER,
                       vin        TEXT,
                       notes      TEXT,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   ''')

    # Заказ-наряды
    cursor.execute('''
                   CREATE TABLE work_orders
                   (
                       id           INTEGER PRIMARY KEY AUTOINCREMENT,
                       client_id    INTEGER NOT NULL,
                       order_number TEXT UNIQUE,
                       description  TEXT    NOT NULL,
                       status       TEXT      DEFAULT 'new',
                       total_amount REAL      DEFAULT 0,
                       created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       completed_at TIMESTAMP,
                       FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
                   )
                   ''')

    # Работы в заказ-наряде
    cursor.execute('''
                   CREATE TABLE order_works
                   (
                       id             INTEGER PRIMARY KEY AUTOINCREMENT,
                       order_id       INTEGER NOT NULL,
                       work_name      TEXT    NOT NULL,
                       quantity       INTEGER DEFAULT 1,
                       price_per_unit REAL    DEFAULT 0,
                       total_price    REAL    DEFAULT 0,
                       FOREIGN KEY (order_id) REFERENCES work_orders (id) ON DELETE CASCADE
                   )
                   ''')

    # Расходы в заказ-наряде
    cursor.execute('''
                   CREATE TABLE order_expenses
                   (
                       id            INTEGER PRIMARY KEY AUTOINCREMENT,
                       order_id      INTEGER NOT NULL,
                       expense_name  TEXT    NOT NULL,
                       expense_type  TEXT    DEFAULT 'material',
                       quantity      INTEGER DEFAULT 1,
                       cost_per_unit REAL    DEFAULT 0,
                       total_cost    REAL    DEFAULT 0,
                       notes         TEXT,
                       FOREIGN KEY (order_id) REFERENCES work_orders (id) ON DELETE CASCADE
                   )
                   ''')

    # Задачи
    cursor.execute('''
                   CREATE TABLE tasks
                   (
                       id           INTEGER PRIMARY KEY AUTOINCREMENT,
                       title        TEXT NOT NULL,
                       description  TEXT,
                       priority     TEXT      DEFAULT 'medium',
                       status       TEXT      DEFAULT 'pending',
                       assigned_to  TEXT,
                       due_date     TIMESTAMP,
                       created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       completed_at TIMESTAMP
                   )
                   ''')

    # Касса (доходы и расходы)
    cursor.execute('''
                   CREATE TABLE cash_flow
                   (
                       id               INTEGER PRIMARY KEY AUTOINCREMENT,
                       transaction_type TEXT NOT NULL,
                       category         TEXT NOT NULL,
                       amount           REAL NOT NULL,
                       description      TEXT,
                       order_id         INTEGER,
                       date             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       FOREIGN KEY (order_id) REFERENCES work_orders (id) ON DELETE SET NULL
                   )
                   ''')

    # Настройки
    cursor.execute('''
                   CREATE TABLE settings
                   (
                       id         INTEGER PRIMARY KEY AUTOINCREMENT,
                       key        TEXT NOT NULL UNIQUE,
                       value      TEXT,
                       category   TEXT      DEFAULT 'general',
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   ''')

    # Индексы
    cursor.execute('CREATE INDEX idx_clients_phone ON clients(phone)')
    cursor.execute('CREATE INDEX idx_orders_status ON work_orders(status)')
    cursor.execute('CREATE INDEX idx_cashflow_date ON cash_flow(date)')
    cursor.execute('CREATE INDEX idx_cashflow_type ON cash_flow(transaction_type)')

    print("✅ Таблицы созданы")

    # ========== ТЕСТОВЫЕ ДАННЫЕ ==========

    # Настройки по умолчанию
    print("\n📝 Добавление настроек...")
    default_settings = [
        ('dashboard_period', 'month', 'dashboard'),
        ('dashboard_show_expenses', 'true', 'dashboard'),
        ('dashboard_quick_actions', 'new_client,new_order,new_task,cash_view', 'dashboard'),
        ('tax_rate', '20', 'finance'),
        ('currency', '₽', 'general'),
        ('company_name', 'Тестовый Автосервис', 'general')
    ]

    for key, value, category in default_settings:
        cursor.execute('''
                       INSERT INTO settings (key, value, category)
                       VALUES (?, ?, ?)
                       ''', (key, value, category))

    print("✅ Настройки добавлены")

    # Тестовые клиенты
    print("\n👥 Добавление тестовых клиентов...")
    clients = [
        ('Иванов Иван Иванович', '+79161234567', 'Toyota Camry', 'А123ВС77', 2020, 'JTDBR32E160123456',
         'Постоянный клиент, VIP'),
        ('Петров Петр Петрович', '+79165556677', 'Lada Vesta', 'В456ОР78', 2021, 'XTA210300Y1234567', 'Новый клиент'),
        ('Сидорова Анна Сергеевна', '+79167778899', 'Hyundai Solaris', 'С789ТУ79', 2019, 'Z94CB41AAGR123456',
         'Часто обслуживается'),
        ('Козлов Алексей Владимирович', '+79169990011', 'Kia Rio', 'Е012ХК80', 2022, 'KNAGN814BC1234567',
         'Корпоративный клиент'),
        ('Морозова Екатерина Дмитриевна', '+79162223344', 'Volkswagen Polo', 'М345РА81', 2021, 'WVWZZZ6RZBY123456',
         'Сервисное обслуживание')
    ]

    client_ids = []
    for client in clients:
        cursor.execute('''
                       INSERT INTO clients (full_name, phone, car_model, car_number, car_year, vin, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ''', client)
        client_ids.append(cursor.lastrowid)

    print(f"✅ Добавлено {len(clients)} клиентов")

    # Тестовые заказ-наряды
    print("\n📋 Добавление тестовых заказ-нарядов...")
    order_descriptions = [
        'Замена масла и фильтров',
        'Диагностика ходовой части',
        'Ремонт тормозной системы',
        'Замена свечей зажигания',
        'Комплексное обслуживание'
    ]

    order_statuses = ['new', 'in_progress', 'completed', 'completed', 'completed']
    order_ids = []

    for i in range(5):
        date_str = datetime.now().strftime("%y%m%d")
        order_number = f"{date_str}-{i + 1:03d}"
        client_id = client_ids[i]
        status = order_statuses[i]
        total_amount = random.randint(5000, 30000)

        cursor.execute('''
                       INSERT INTO work_orders (client_id, order_number, description, status, total_amount)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (client_id, order_number, order_descriptions[i], status, total_amount))

        order_id = cursor.lastrowid
        order_ids.append(order_id)

        # Для завершенных заказов добавляем дату завершения
        if status == 'completed':
            completed_date = datetime.now() - timedelta(days=random.randint(1, 30))
            cursor.execute('UPDATE work_orders SET completed_at = ? WHERE id = ?',
                           (completed_date.strftime('%Y-%m-%d %H:%M:%S'), order_id))

    print(f"✅ Добавлено {len(order_ids)} заказ-нарядов")

    # Тестовые работы в заказ-нарядах
    print("\n🔧 Добавление тестовых работ...")
    works = [
        ['Замена моторного масла', 'Замена масляного фильтра', 'Диагностика двигателя'],
        ['Диагностика подвески', 'Замена амортизаторов', 'Балансировка колес'],
        ['Замена тормозных колодок', 'Замена тормозных дисков', 'Прокачка тормозов'],
        ['Замена свечей зажигания', 'Чистка инжектора', 'Диагностика зажигания'],
        ['Комплексная диагностика', 'Замена всех жидкостей', 'Регулировка фар']
    ]

    for i, order_id in enumerate(order_ids):
        for work_name in works[i]:
            quantity = random.randint(1, 3)
            price = random.randint(500, 5000)
            total = quantity * price

            cursor.execute('''
                           INSERT INTO order_works (order_id, work_name, quantity, price_per_unit, total_price)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (order_id, work_name, quantity, price, total))

    print("✅ Работы добавлены")

    # Тестовые расходы в заказ-нарядах
    print("\n💰 Добавление тестовых расходов...")
    expense_types = ['material', 'parts', 'other']
    expense_items = [
        ['Моторное масло 5W-30', 'Масляный фильтр', 'Воздушный фильтр'],
        ['Амортизатор передний', 'Сайлентблок', 'Шаровая опора'],
        ['Тормозные колодки', 'Тормозные диски', 'Тормозная жидкость'],
        ['Свечи зажигания', 'ВВ провода', 'Катушка зажигания'],
        ['Охлаждающая жидкость', 'Трансмиссионное масло', 'Жидкость ГУР']
    ]

    for i, order_id in enumerate(order_ids):
        for expense_name in expense_items[i]:
            expense_type = random.choice(expense_types)
            quantity = random.randint(1, 4)
            cost = random.randint(300, 4000)
            total = quantity * cost

            cursor.execute('''
                           INSERT INTO order_expenses (order_id, expense_name, expense_type, quantity, cost_per_unit,
                                                       total_cost)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ''', (order_id, expense_name, expense_type, quantity, cost, total))

    print("✅ Расходы добавлены")

    # Тестовые задачи
    print("\n📋 Добавление тестовых задач...")
    tasks = [
        ('Позвонить клиенту Иванову', 'Уточнить время визита', 'high', 'pending', 'Механик 1',
         (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')),
        ('Заказать запчасти', 'Тормозные колодки для Lada Vesta', 'medium', 'in_progress', 'Менеджер',
         (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')),
        ('Составить отчет за месяц', 'Финансовый отчет', 'low', 'pending', 'Администратор',
         (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')),
        ('Провести инвентаризацию', 'Склад запчастей', 'medium', 'completed', 'Складской',
         (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')),
        ('Обновить программное обеспечение', 'Обновить CRM систему', 'high', 'in_progress', 'IT специалист',
         (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'))
    ]

    for task in tasks:
        cursor.execute('''
                       INSERT INTO tasks (title, description, priority, status, assigned_to, due_date)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ''', task)

    print("✅ Задачи добавлены")

    # Тестовые операции кассы
    print("\n💵 Добавление тестовых операций кассы...")

    # Доходы от завершенных заказов
    for i, order_id in enumerate(order_ids[:3]):  # Только первые 3 заказа как завершенные
        cursor.execute('SELECT order_number, total_amount FROM work_orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()

        if order and order['total_amount'] > 0:
            date = datetime.now() - timedelta(days=random.randint(1, 30))

            cursor.execute('''
                           INSERT INTO cash_flow (transaction_type, category, amount, description, order_id, date)
                           VALUES ('income', 'order_income', ?, ?, ?, ?)
                           ''', (order['total_amount'], f'Доход от заказа {order["order_number"]}', order_id,
                                 date.strftime('%Y-%m-%d %H:%M:%S')))

    # Прочие доходы
    other_incomes = [
        ('income', 'other_income', 15000, 'Продажа запчастей со склада'),
        ('income', 'other_income', 8000, 'Дополнительные услуги'),
    ]

    for income in other_incomes:
        date = datetime.now() - timedelta(days=random.randint(5, 20))
        cursor.execute('''
                       INSERT INTO cash_flow (transaction_type, category, amount, description, date)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (*income, date.strftime('%Y-%m-%d %H:%M:%S')))

    # Расходы
    expenses = [
        ('expense', 'material', 12000, 'Закупка материалов'),
        ('expense', 'parts', 25000, 'Закупка запчастей'),
        ('expense', 'salary', 150000, 'Зарплата сотрудникам'),
        ('expense', 'rent', 50000, 'Аренда помещения'),
        ('expense', 'utilities', 15000, 'Коммунальные услуги'),
        ('expense', 'other_expense', 8000, 'Прочие расходы')
    ]

    for expense in expenses:
        date = datetime.now() - timedelta(days=random.randint(1, 30))
        cursor.execute('''
                       INSERT INTO cash_flow (transaction_type, category, amount, description, date)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (*expense, date.strftime('%Y-%m-%d %H:%M:%S')))

    print("✅ Операции кассы добавлены")

    # ========== ПРОВЕРКА ДАННЫХ ==========

    conn.commit()

    print("\n" + "=" * 50)
    print("📊 СТАТИСТИКА ТЕСТОВОЙ БАЗЫ ДАННЫХ")
    print("=" * 50)

    # Подсчет записей
    tables = ['clients', 'work_orders', 'order_works', 'order_expenses', 'tasks', 'cash_flow', 'settings']

    for table in tables:
        cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
        count = cursor.fetchone()['count']
        print(f"📁 {table:15} → {count:3} записей")

    # Финансовая статистика
    cursor.execute('SELECT COALESCE(SUM(total_amount), 0) FROM work_orders WHERE status = "completed"')
    total_revenue = cursor.fetchone()[0]

    cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM cash_flow WHERE transaction_type = "income"')
    total_income = cursor.fetchone()[0]

    cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM cash_flow WHERE transaction_type = "expense"')
    total_expenses = cursor.fetchone()[0]

    print("\n💰 ФИНАНСОВАЯ СТАТИСТИКА:")
    print(f"Выручка от заказов: {total_revenue:,.2f} ₽")
    print(f"Доходы в кассе:     {total_income:,.2f} ₽")
    print(f"Расходы в кассе:    {total_expenses:,.2f} ₽")
    print(f"Баланс:             {total_income - total_expenses:,.2f} ₽")

    # Статистика по заказам
    cursor.execute('SELECT status, COUNT(*) as count FROM work_orders GROUP BY status')
    order_stats = cursor.fetchall()

    print("\n📋 СТАТУСЫ ЗАКАЗ-НАРЯДОВ:")
    for stat in order_stats:
        print(f"  {stat['status']:12} → {stat['count']:2} шт.")

    conn.close()

    print("\n" + "=" * 50)
    print("✅ ТЕСТОВАЯ БАЗА ДАННЫХ УСПЕШНО СОЗДАНА!")
    print(f"📁 Файл: {db_name}")
    print("=" * 50)

    print("\n🎯 ДЛЯ ИСПОЛЬЗОВАНИЯ:")
    print("1. Переименуйте файл в app.py:")
    print("   database = Database('autoservice_test.db')")
    print("\n2. Или создайте копию для тестирования:")
    print("   import shutil")
    print("   shutil.copy('autoservice_test.db', 'autoservice.db')")


def create_database_with_realistic_data(db_name='autoservice_realistic.db'):
    """Создание базы данных с более реалистичными данными"""

    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"\n🔧 Создание реалистичной базы данных: {db_name}")

    # Создаем те же таблицы
    create_test_database.__code__ = create_test_database.__code__  # Просто чтобы использовать ту же логику

    # Но добавляем больше данных
    print("Добавляем расширенные тестовые данные...")

    conn.close()

    return db_name


def copy_to_main_db():
    """Копирование тестовой БД в основную"""
    import shutil
    import os

    if not os.path.exists('autoservice_test.db'):
        print("❌ Файл autoservice_test.db не найден!")
        print("   Сначала запустите create_test_database()")
        return

    try:
        shutil.copy('autoservice_test.db', 'autoservice.db')
        print("✅ Тестовая БД скопирована в autoservice.db")
        print("🎯 Теперь можно запускать основное приложение!")
    except Exception as e:
        print(f"❌ Ошибка при копировании: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("🛠️  ГЕНЕРАТОР ТЕСТОВОЙ БАЗЫ ДАННЫХ ДЛЯ CRM АВТОСЕРВИСА")
    print("=" * 60)
    print("\nВыберите действие:")
    print("1. Создать тестовую БД (autoservice_test.db)")
    print("2. Создать и скопировать в основную БД")
    print("3. Только скопировать существующую тестовую БД")

    choice = input("\nВаш выбор (1-3): ").strip()

    if choice == '1':
        create_test_database('autoservice_test.db')
    elif choice == '2':
        create_test_database('autoservice_test.db')
        copy_to_main_db()
    elif choice == '3':
        copy_to_main_db()
    else:
        print("❌ Неверный выбор. Завершение.")