from flask import Flask, render_template, request, jsonify
from database import Database
from datetime import datetime, timedelta
import traceback

app = Flask(__name__)

# Инициализация базы данных
db = Database()


# Фильтр для форматирования чисел
@app.template_filter('format_money')
def format_money(value):
    """Фильтр для форматирования денежных значений"""
    try:
        return f"{float(value):.2f}"
    except:
        return value


# ========== ОСНОВНЫЕ СТРАНИЦЫ ==========

@app.route('/')
def index():
    """Главная страница"""
    stats = db.get_stats()
    return render_template('index.html', stats=stats)


@app.route('/clients')
def clients_page():
    """Страница клиентов"""
    search_term = request.args.get('search', '')
    clients = db.get_clients(search_term)
    # Конвертируем Row объекты в словари
    clients_list = [dict(client) for client in clients]
    return render_template('clients.html', clients=clients_list, search_term=search_term)


@app.route('/work_orders')
def work_orders_page():
    """Страница заказ-нарядов"""
    search_term = request.args.get('search', '')
    orders = db.get_work_orders(search_term)
    # Конвертируем Row объекты в словари
    orders_list = [dict(order) for order in orders]
    return render_template('work_orders.html', orders=orders_list, search_term=search_term)


@app.route('/new_work_order')
def new_work_order_page():
    """Страница создания нового заказ-наряда"""
    client_id = request.args.get('client_id', '')
    clients = db.get_clients()
    employees = db.get_active_employees()
    # Конвертируем Row объекты в словари
    clients_list = [dict(client) for client in clients]
    employees_list = [dict(employee) for employee in employees]
    return render_template('new_work_order.html',
                           clients=clients_list,
                           employees=employees_list,
                           selected_client_id=client_id)


@app.route('/edit_work_order/<int:order_id>')
def edit_work_order_page(order_id):
    """Страница редактирования заказ-наряда"""
    order = db.get_work_order(order_id)
    if not order:
        return "Заказ-наряд не найден", 404

    # Конвертируем Row в словарь
    order_dict = dict(order)

    if order_dict['status'] == 'completed':
        return "Невозможно редактировать завершенный заказ", 400

    clients = db.get_clients()
    employees = db.get_active_employees()
    # Конвертируем Row объекты в словари
    clients_list = [dict(client) for client in clients]
    employees_list = [dict(employee) for employee in employees]

    return render_template('edit_work_order.html',
                           order=order_dict,
                           clients=clients_list,
                           employees=employees_list)


@app.route('/tasks')
def tasks_page():
    """Страница задач"""
    status = request.args.get('status', '')
    tasks = db.get_tasks(status if status else None)
    tasks_list = [dict(task) for task in tasks]
    return render_template('tasks.html', tasks=tasks_list)


@app.route('/cash')
def cash_page():
    """Страница кассы"""
    period = request.args.get('period', 'month')
    transaction_type = request.args.get('type', '')
    selected_category = request.args.get('category', '')

    # Определяем даты для периода
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
        start_date = end_date - timedelta(days=30)

    # Получаем операции с фильтрацией
    cash_flow = db.get_cash_flow(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        transaction_type if transaction_type else None,
        selected_category if selected_category else None
    )

    # Конвертируем Row объекты в словари
    cash_flow_list = [dict(cf) for cf in cash_flow]

    # Финансовая статистика
    financial_stats = db.get_financial_stats(period)
    total_balance = db.get_total_balance()

    # Категории для фильтров
    income_categories = ['order_work', 'order_markup', 'salary_paid', 'cash_in', 'other_income']
    expense_categories = ['salary', 'parts_purchase', 'rent', 'utilities', 'cash_out', 'other_expense']

    # Названия категорий
    cat_names = {
        'order_work': 'Работы по заказу',
        'order_markup': 'Наценка на запчасти',
        'salary_paid': 'Выплата зарплаты',
        'cash_in': 'Внесение наличных',
        'other_income': 'Прочий доход',
        'salary': 'Зарплата',
        'parts_purchase': 'Покупка запчастей',
        'rent': 'Аренда',
        'utilities': 'Коммунальные',
        'cash_out': 'Изъятие наличных',
        'other_expense': 'Прочие расходы'
    }

    return render_template('cash.html',
                           cash_flow=cash_flow_list,
                           financial_stats=financial_stats,
                           total_balance=total_balance,
                           period=period,
                           transaction_type=transaction_type,
                           selected_category=selected_category,
                           income_categories=income_categories,
                           expense_categories=expense_categories,
                           cat_names=cat_names)


@app.route('/employees')
def employees_page():
    """Страница работников"""
    employees = db.get_employees_with_salary()

    # Рассчитываем общую статистику
    total_salary = sum([e.get('earned_amount', 0) or 0 for e in employees])
    paid_salary = sum([e.get('paid_amount', 0) or 0 for e in employees])
    pending_salary = total_salary - paid_salary

    return render_template('employees.html',
                           employees=employees,
                           total_salary=total_salary,
                           paid_salary=paid_salary,
                           pending_salary=pending_salary)


# ========== API ДЛЯ КЛИЕНТОВ ==========

@app.route('/api/clients/add', methods=['POST'])
def add_client():
    """Добавление нового клиента"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()

        required_fields = ['full_name', 'phone', 'car_model']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Отсутствует поле: {field}'}), 400

        client_id = db.add_client(
            full_name=data['full_name'],
            phone=data['phone'],
            car_model=data['car_model'],
            car_number=data.get('car_number', ''),
            car_year=data.get('car_year'),
            vin=data.get('vin', ''),
            notes=data.get('notes', '')
        )

        return jsonify({
            'success': True,
            'client_id': client_id,
            'message': 'Клиент успешно добавлен'
        })

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 409
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/clients/<int:client_id>', methods=['GET', 'PUT', 'DELETE'])
def client_operations(client_id):
    """Операции с клиентом"""
    try:
        if request.method == 'GET':
            client = db.get_client(client_id)
            if client:
                return jsonify({'success': True, 'client': dict(client)})
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404

        elif request.method == 'PUT':
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

            data = request.get_json()
            success = db.update_client(client_id, **data)

            if success:
                return jsonify({'success': True, 'message': 'Клиент обновлен'})
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404

        elif request.method == 'DELETE':
            success = db.delete_client(client_id)
            if success:
                return jsonify({'success': True, 'message': 'Клиент удален'})
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== API ДЛЯ ЗАКАЗ-НАРЯДОВ ==========

# В методе add_work_order в app.py исправьте генерацию номера заказа:
@app.route('/api/work_orders/add', methods=['POST'])
def add_work_order():
    """Добавление нового заказ-наряда"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()
        print(f"Получены данные для создания заказа: {data}")

        if not data.get('client_id'):
            return jsonify({'success': False, 'error': 'Отсутствует client_id'}), 400
        if not data.get('description'):
            return jsonify({'success': False, 'error': 'Отсутствует description'}), 400

        # Рассчитываем суммы
        works_total = 0
        expenses_price = 0
        markup_total = 0

        # Работы
        for work in data.get('works', []):
            quantity = work.get('quantity', 1)
            price = work.get('price', 0)
            works_total += quantity * price

        # Запчасти и расходники с наценкой
        for expense in data.get('expenses', []):
            quantity = expense.get('quantity', 1)
            cost = expense.get('cost', 0)
            markup = expense.get('markup', 0)

            if cost > 0:
                item_cost = quantity * cost
                item_price = item_cost * (1 + markup / 100)
                expenses_price += item_price
                markup_total += item_price - item_cost

        # Округляем
        works_total = round(works_total, 2)
        expenses_price = round(expenses_price, 2)
        markup_total = round(markup_total, 2)
        total_amount = works_total + expenses_price

        # Используем переданный номер или генерируем новый
        order_number = data.get('order_number')
        if not order_number or order_number == 'Загрузка...':
            # Генерируем номер
            date_str = datetime.now().strftime("%y%m%d")
            try:
                cursor = db.conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM work_orders WHERE order_number LIKE ?', (f'{date_str}%',))
                count = cursor.fetchone()[0] + 1
                order_number = f"{date_str}-{count:03d}"
            except:
                order_number = f"{date_str}-001"

        order_id = db.add_work_order(
            client_id=data['client_id'],
            description=data['description'],
            order_number=order_number,
            total_amount=total_amount,
            employee_id=data.get('employee_id')
        )

        if not order_id:
            return jsonify({'success': False, 'error': 'Не удалось создать заказ-наряд'}), 500

        print(f"Создан заказ ID: {order_id}, номер: {order_number}")

        # Сохраняем работы
        for work in data.get('works', []):
            db.add_order_work(
                order_id=order_id,
                work_name=work['name'],
                quantity=work.get('quantity', 1),
                price_per_unit=work.get('price', 0)
            )

        # Сохраняем запчасти с наценкой
        for expense in data.get('expenses', []):
            db.add_order_expense(
                order_id=order_id,
                expense_name=expense['name'],
                expense_type=expense.get('type', 'material'),
                quantity=expense.get('quantity', 1),
                cost_per_unit=expense.get('cost', 0),
                markup=expense.get('markup', 0)
            )

        order = db.get_work_order(order_id)

        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_number': order['order_number'] if order else order_number,
            'total_amount': total_amount,
            'works_total': works_total,
            'expenses_price': expenses_price,
            'markup_total': markup_total,
            'message': 'Заказ-наряд создан'
        })

    except Exception as e:
        print(f"❌ Ошибка в add_work_order: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/work_orders/<int:order_id>', methods=['GET', 'PUT', 'DELETE'])
def work_order_operations(order_id):
    """Операции с заказ-нарядом"""
    try:
        if request.method == 'GET':
            order = db.get_work_order(order_id)
            if order:
                works = db.get_order_works(order_id)
                expenses = db.get_order_expenses(order_id)

                print(f"Загружен заказ ID: {order_id}")  # Отладочный вывод
                print(f"Найдено работ: {len(works)}")  # Отладочный вывод
                print(f"Найдено запчастей: {len(expenses)}")  # Отладочный вывод

                return jsonify({
                    'success': True,
                    'order': dict(order),
                    'works': [dict(w) for w in works],
                    'expenses': [dict(e) for e in expenses]
                })
            return jsonify({'success': False, 'error': 'Заказ-наряд не найден'}), 404

        elif request.method == 'PUT':
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

            data = request.get_json()
            print(f"Получены данные для обновления заказа {order_id}: {data}")  # Отладочный вывод

            # Получаем текущий заказ
            order = db.get_work_order(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Заказ-наряд не найден'}), 404

            order_dict = dict(order)
            if order_dict['status'] == 'completed':
                return jsonify({'success': False, 'error': 'Невозможно редактировать завершенный заказ'}), 400

            # Рассчитываем суммы
            works_total = 0
            expenses_price = 0
            markup_total = 0

            # Работы
            for work in data.get('works', []):
                quantity = work.get('quantity', 1)
                price = work.get('price', 0)
                works_total += quantity * price

            # Запчасти с наценкой
            for expense in data.get('expenses', []):
                quantity = expense.get('quantity', 1)
                cost = expense.get('cost', 0)
                markup = expense.get('markup', 0)

                if cost > 0:
                    item_cost = quantity * cost
                    item_price = item_cost * (1 + markup / 100)
                    expenses_price += item_price
                    markup_total += item_price - item_cost

            # Округляем
            works_total = round(works_total, 2)
            expenses_price = round(expenses_price, 2)
            markup_total = round(markup_total, 2)
            total_amount = works_total + expenses_price

            # Обновляем заказ
            success = db.update_work_order(
                order_id=order_id,
                client_id=data.get('client_id', order_dict['client_id']),
                description=data.get('description', order_dict['description']),
                total_amount=total_amount,
                employee_id=data.get('employee_id')
            )

            if not success:
                return jsonify({'success': False, 'error': 'Не удалось обновить заказ-наряд'}), 500

            # Удаляем старые работы и запчасти
            db.delete_order_works(order_id)
            db.delete_order_expenses(order_id)

            # Сохраняем новые работы
            for work in data.get('works', []):
                db.add_order_work(
                    order_id=order_id,
                    work_name=work['name'],
                    quantity=work.get('quantity', 1),
                    price_per_unit=work.get('price', 0)
                )

            # Сохраняем новые запчасти
            for expense in data.get('expenses', []):
                db.add_order_expense(
                    order_id=order_id,
                    expense_name=expense['name'],
                    expense_type=expense.get('type', 'material'),
                    quantity=expense.get('quantity', 1),
                    cost_per_unit=expense.get('cost', 0),
                    markup=expense.get('markup', 0)
                )

            return jsonify({
                'success': True,
                'message': 'Заказ-наряд обновлен',
                'total_amount': total_amount,
                'works_total': works_total,
                'expenses_price': expenses_price,
                'markup_total': markup_total
            })

        elif request.method == 'DELETE':
            success = db.delete_work_order(order_id)
            if success:
                return jsonify({'success': True, 'message': 'Заказ-наряд удален'})
            return jsonify({'success': False, 'error': 'Заказ-наряд не найден'}), 404

    except Exception as e:
        print(f"Ошибка в work_order_operations: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/work_orders/<int:order_id>/complete', methods=['POST'])
def complete_work_order(order_id):
    """Завершение заказ-наряда"""
    try:
        # Получаем информацию о заказе
        order = db.get_work_order(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Заказ-наряд не найден'}), 404

        # Конвертируем Row в словарь
        order_dict = dict(order)

        # Обновляем статус
        success = db.update_work_order_status(order_id, 'completed')
        if not success:
            return jsonify({'success': False, 'error': 'Не удалось обновить статус'}), 500

        # Получаем работы и запчасти
        works = db.get_order_works(order_id)
        expenses = db.get_order_expenses(order_id)

        # Рассчитываем суммы
        works_total = sum([w['quantity'] * w['price_per_unit'] for w in works])
        markup_total = 0

        # Рассчитываем наценку на запчасти
        for expense in expenses:
            cost = expense['cost_per_unit']
            markup = expense['markup']
            quantity = expense['quantity']

            if cost > 0:
                item_cost = cost * quantity
                item_price = item_cost * (1 + (markup or 0) / 100)
                markup_total += item_price - item_cost

        # Округляем
        works_total = round(works_total, 2)
        markup_total = round(markup_total, 2)

        # Добавляем доход от работ в кассу
        if works_total > 0:
            db.add_cash_flow(
                transaction_type='income',
                category='order_work',
                amount=works_total,
                description=f'Доход от работ по заказу {order_dict["order_number"]}',
                order_id=order_id
            )

        # Добавляем наценку на запчасти в кассу
        if markup_total > 0:
            db.add_cash_flow(
                transaction_type='income',
                category='order_markup',
                amount=markup_total,
                description=f'Наценка на запчасти по заказу {order_dict["order_number"]}',
                order_id=order_id
            )

        # Если есть работник, рассчитываем и добавляем зарплату
        if order_dict.get('employee_id'):
            employee = db.get_employee(order_dict['employee_id'])
            if employee and employee['commission_rate'] > 0:
                commission_rate = employee['commission_rate']
                salary_amount = round(works_total * commission_rate / 100, 2)

                if salary_amount > 0:
                    # Добавляем зарплату в начисления
                    db.add_employee_salary(
                        employee_id=order_dict['employee_id'],
                        order_id=order_id,
                        amount=salary_amount,
                        commission_rate=commission_rate,
                        works_total=works_total
                    )

        return jsonify({
            'success': True,
            'message': 'Заказ-наряд завершен',
            'works_total': works_total,
            'markup_total': markup_total,
            'total_income': works_total + markup_total
        })

    except Exception as e:
        print(f"Ошибка при завершении заказа: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/work_orders/last_number')
def get_last_order_number():
    """Получение последнего номера заказа"""
    try:
        date_prefix = request.args.get('date', '')
        if not date_prefix:
            date_prefix = datetime.now().strftime('%y%m%d')

        cursor = db.conn.cursor()
        cursor.execute('''
                       SELECT order_number
                       FROM work_orders
                       WHERE order_number LIKE ?
                       ORDER BY id DESC LIMIT 1
                       ''', (f'{date_prefix}%',))

        result = cursor.fetchone()

        if result:
            last_number = result[0]
            # Парсим номер формата YYMMDD-XXX
            import re
            match = re.match(r'(\d{6})-(\d{3})', last_number)
            if match:
                prefix = match.group(1)
                num = int(match.group(2))
                next_num = f"{prefix}-{num + 1:03d}"
            else:
                next_num = f"{date_prefix}-001"
        else:
            next_num = f"{date_prefix}-001"

        return jsonify({
            'success': True,
            'next_number': next_num
        })

    except Exception as e:
        return jsonify({
            'success': True,
            'next_number': f"{datetime.now().strftime('%y%m%d')}-001"
        })

# ========== API ДЛЯ ЗАДАЧ ==========

@app.route('/api/tasks/add', methods=['POST'])
def add_task():
    """Добавление новой задачи"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()

        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Отсутствует title'}), 400

        task_id = db.add_task(
            title=data['title'],
            description=data.get('description', ''),
            priority=data.get('priority', 'medium'),
            assigned_to=data.get('assigned_to', ''),
            due_date=data.get('due_date')
        )

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Задача создана'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def task_operations(task_id):
    """Операции с задачей"""
    try:
        if request.method == 'GET':
            task = db.get_task(task_id)
            if task:
                return jsonify({'success': True, 'task': dict(task)})
            return jsonify({'success': False, 'error': 'Задача не найдена'}), 404

        elif request.method == 'PUT':
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

            data = request.get_json()

            if data.get('status') == 'completed' and 'completed_at' not in data:
                data['completed_at'] = datetime.now().isoformat()

            success = db.update_task(task_id, **data)
            if success:
                return jsonify({'success': True, 'message': 'Задача обновлена'})
            return jsonify({'success': False, 'error': 'Задача не найдена'}), 404

        elif request.method == 'DELETE':
            success = db.delete_task(task_id)
            if success:
                return jsonify({'success': True, 'message': 'Задача удалена'})
            return jsonify({'success': False, 'error': 'Задача не найдена'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== API ДЛЯ КАССЫ ==========

@app.route('/api/cash/add', methods=['POST'])
def add_cash_flow():
    """Добавление операции в кассу"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()

        if not data.get('transaction_type'):
            return jsonify({'success': False, 'error': 'Отсутствует transaction_type'}), 400
        if not data.get('category'):
            return jsonify({'success': False, 'error': 'Отсутствует category'}), 400
        if not data.get('amount'):
            return jsonify({'success': False, 'error': 'Отсутствует amount'}), 400
        if not data.get('description'):
            return jsonify({'success': False, 'error': 'Отсутствует description'}), 400

        flow_id = db.add_cash_flow(
            transaction_type=data['transaction_type'],
            category=data['category'],
            amount=data['amount'],
            description=data['description'],
            order_id=data.get('order_id')
        )

        return jsonify({
            'success': True,
            'flow_id': flow_id,
            'message': 'Операция добавлена'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cash/stats')
def get_cash_stats():
    """Получение финансовой статистики"""
    try:
        period = request.args.get('period', 'month')
        stats = db.get_financial_stats(period)
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== API ДЛЯ РАБОТНИКОВ ==========

@app.route('/api/employees/add', methods=['POST'])
def add_employee():
    """Добавление нового работника"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()

        if not data.get('full_name'):
            return jsonify({'success': False, 'error': 'Отсутствует full_name'}), 400
        if not data.get('position'):
            return jsonify({'success': False, 'error': 'Отсутствует position'}), 400
        if not data.get('commission_rate'):
            return jsonify({'success': False, 'error': 'Отсутствует commission_rate'}), 400

        employee_id = db.add_employee(
            full_name=data['full_name'],
            position=data['position'],
            phone=data.get('phone', ''),
            commission_rate=data['commission_rate'],
            hire_date=data.get('hire_date'),
            is_active=data.get('is_active', True),
            notes=data.get('notes', '')
        )

        return jsonify({
            'success': True,
            'employee_id': employee_id,
            'message': 'Работник успешно добавлен'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:employee_id>', methods=['GET', 'PUT'])
def employee_operations(employee_id):
    """Операции с работником"""
    try:
        if request.method == 'GET':
            employee = db.get_employee_with_salary(employee_id)
            if employee:
                return jsonify({'success': True, 'employee': dict(employee)})
            return jsonify({'success': False, 'error': 'Работник не найден'}), 404

        elif request.method == 'PUT':
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

            data = request.get_json()
            success = db.update_employee(employee_id, **data)

            if success:
                return jsonify({'success': True, 'message': 'Работник обновлен'})
            return jsonify({'success': False, 'error': 'Работник не найден'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:employee_id>/status', methods=['PUT'])
def update_employee_status(employee_id):
    """Обновление статуса работника"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()
        if 'is_active' not in data:
            return jsonify({'success': False, 'error': 'Отсутствует is_active'}), 400

        success = db.update_employee_status(employee_id, data['is_active'])
        if success:
            return jsonify({'success': True, 'message': 'Статус обновлен'})
        return jsonify({'success': False, 'error': 'Работник не найден'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<int:employee_id>/pay', methods=['POST'])
def pay_employee_salary(employee_id):
    """Выплата зарплаты работнику"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()
        if not data.get('amount'):
            return jsonify({'success': False, 'error': 'Отсутствует amount'}), 400

        amount = float(data['amount'])

        # Получаем информацию о работнике
        employee = db.get_employee_with_salary(employee_id)
        if not employee:
            return jsonify({'success': False, 'error': 'Работник не найден'}), 404

        earned = employee.get('earned_amount', 0) or 0
        paid = employee.get('paid_amount', 0) or 0
        pending = earned - paid

        if amount > pending:
            return jsonify({'success': False, 'error': f'Сумма превышает задолженность ({pending:.2f} ₽)'}), 400

        # Добавляем выплату
        payment_id = db.add_salary_payment(
            employee_id=employee_id,
            amount=amount,
            description=f'Выплата зарплаты {employee["full_name"]}'
        )

        if payment_id:
            # Добавляем операцию в кассу как расход
            db.add_cash_flow(
                transaction_type='expense',
                category='salary',
                amount=amount,
                description=f'Выплата зарплаты работнику {employee["full_name"]}'
            )

            return jsonify({
                'success': True,
                'message': 'Зарплата выплачена',
                'amount': amount,
                'pending': pending - amount
            })

        return jsonify({'success': False, 'error': 'Ошибка при выплате зарплаты'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

if __name__ == '__main__':
    print("🚀 Запуск CRM Автосервиса...")
    app.run(debug=True, port=5000)