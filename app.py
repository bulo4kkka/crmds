from flask import Flask, render_template, request, jsonify
from database import Database
from datetime import datetime, timedelta
import traceback

app = Flask(__name__)

# Инициализация базы данных
db = Database()


# ========== ОСНОВНЫЕ СТРАНИЦЫ ==========

@app.route('/')
def index():
    """Главная страница"""
    stats = db.get_stats()
    settings_data = db.get_all_settings()

    # Получаем настройки дашборда
    dashboard_settings = settings_data.get('dashboard', [])
    settings_dict = {}
    for setting in dashboard_settings:
        settings_dict[setting['key']] = setting['value']

    quick_actions = settings_dict.get('dashboard_quick_actions', 'new_client,new_order,new_task,cash_view').split(',')
    period = settings_dict.get('dashboard_period', 'month')

    financial_stats = db.get_financial_stats(period)
    show_expenses = settings_dict.get('dashboard_show_expenses', 'true') == 'true'

    return render_template('index.html',
                           stats=stats,
                           settings=settings_dict,
                           quick_actions=quick_actions,
                           financial_stats=financial_stats,
                           show_expenses=show_expenses,
                           period=period)


@app.route('/clients')
def clients_page():
    """Страница клиентов"""
    search_term = request.args.get('search', '')
    clients = db.get_clients(search_term)
    return render_template('clients.html', clients=clients, search_term=search_term)


@app.route('/work_orders')
def work_orders_page():
    """Страница заказ-нарядов"""
    search_term = request.args.get('search', '')
    orders = db.get_work_orders(search_term)
    return render_template('work_orders.html', orders=orders, search_term=search_term)


@app.route('/new_work_order')
def new_work_order_page():
    """Страница создания нового заказ-наряда"""
    clients = db.get_clients()
    return render_template('new_work_order.html', clients=clients)


@app.route('/tasks')
def tasks_page():
    """Страница задач"""
    status = request.args.get('status', '')
    tasks = db.get_tasks(status if status else None)
    return render_template('tasks.html', tasks=tasks)


@app.route('/cash')
def cash_page():
    """Страница кассы"""
    period = request.args.get('period', 'month')
    transaction_type = request.args.get('type', '')

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

    # Получаем операции
    cash_flow = db.get_cash_flow(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        transaction_type if transaction_type else None
    )

    # Финансовая статистика
    financial_stats = db.get_financial_stats(period)
    total_balance = db.get_total_balance()

    return render_template('cash.html',
                           cash_flow=cash_flow,
                           financial_stats=financial_stats,
                           total_balance=total_balance,
                           period=period,
                           transaction_type=transaction_type)


@app.route('/settings')
def settings_page():
    """Страница настроек"""
    all_settings = db.get_all_settings()
    return render_template('settings.html', settings=all_settings)


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

@app.route('/api/work_orders/add', methods=['POST'])
def add_work_order():
    """Добавление нового заказ-наряда"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()

        if not data.get('client_id'):
            return jsonify({'success': False, 'error': 'Отсутствует client_id'}), 400
        if not data.get('description'):
            return jsonify({'success': False, 'error': 'Отсутствует description'}), 400

        total_amount = 0
        for work in data.get('works', []):
            quantity = work.get('quantity', 1)
            price = work.get('price', 0)
            total_amount += quantity * price

        order_id = db.add_work_order(
            client_id=data['client_id'],
            description=data['description'],
            order_number=data.get('order_number'),
            total_amount=total_amount
        )

        if not order_id:
            return jsonify({'success': False, 'error': 'Не удалось создать заказ-наряд'}), 500

        for work in data.get('works', []):
            db.add_order_work(
                order_id=order_id,
                work_name=work['name'],
                quantity=work.get('quantity', 1),
                price_per_unit=work.get('price', 0)
            )

        for expense in data.get('expenses', []):
            db.add_order_expense(
                order_id=order_id,
                expense_name=expense['name'],
                expense_type=expense.get('type', 'material'),
                quantity=expense.get('quantity', 1),
                cost_per_unit=expense.get('cost', 0),
                notes=expense.get('notes', '')
            )

        order = db.get_work_order(order_id)

        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_number': order['order_number'] if order else '',
            'total_amount': total_amount,
            'message': 'Заказ-наряд создан'
        })

    except Exception as e:
        print(f"❌ Ошибка в add_work_order: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/work_orders/<int:order_id>', methods=['GET', 'DELETE'])
def work_order_operations(order_id):
    """Операции с заказ-нарядом"""
    try:
        if request.method == 'GET':
            order = db.get_work_order(order_id)
            if order:
                works = db.get_order_works(order_id)
                expenses = db.get_order_expenses(order_id)
                return jsonify({
                    'success': True,
                    'order': dict(order),
                    'works': [dict(w) for w in works],
                    'expenses': [dict(e) for e in expenses]
                })
            return jsonify({'success': False, 'error': 'Заказ-наряд не найден'}), 404

        elif request.method == 'DELETE':
            success = db.delete_work_order(order_id)
            if success:
                return jsonify({'success': True, 'message': 'Заказ-наряд удален'})
            return jsonify({'success': False, 'error': 'Заказ-наряд не найден'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/work_orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Обновление статуса заказ-наряда"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()
        if not data.get('status'):
            return jsonify({'success': False, 'error': 'Отсутствует status'}), 400

        success = db.update_work_order_status(order_id, data['status'])
        if success:
            return jsonify({'success': True, 'message': 'Статус обновлен'})
        return jsonify({'success': False, 'error': 'Заказ-наряд не найден'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/work_orders/last_number')
def get_last_order_number():
    """Получение последнего номера заказа"""
    try:
        date_prefix = request.args.get('date', '')
        cursor = db.conn.cursor()

        if date_prefix:
            cursor.execute('''
                           SELECT order_number
                           FROM work_orders
                           WHERE order_number LIKE ?
                           ORDER BY id DESC LIMIT 1
                           ''', (f'{date_prefix}%',))
        else:
            cursor.execute('SELECT order_number FROM work_orders ORDER BY id DESC LIMIT 1')

        result = cursor.fetchone()

        if result:
            last_number = result[0]
            import re
            match = re.match(r'(\d{6})-(\d{3})', last_number)
            if match:
                prefix = match.group(1)
                num = int(match.group(2))
                next_num = f"{prefix}-{num + 1:03d}"
            else:
                next_num = f"{date_prefix}-001"
        else:
            next_num = f"{date_prefix or datetime.now().strftime('%y%m%d')}-001"

        return jsonify({
            'success': True,
            'next_number': next_num
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'next_number': datetime.now().strftime('%y%m%d') + '-001'
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

        flow_id = db.add_cash_flow(
            transaction_type=data['transaction_type'],
            category=data['category'],
            amount=data['amount'],
            description=data.get('description', ''),
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


# ========== API ДЛЯ НАСТРОЕК ==========

@app.route('/api/settings', methods=['GET', 'POST'])
def settings_operations():
    """Операции с настройками"""
    try:
        if request.method == 'GET':
            all_settings = db.get_all_settings()
            return jsonify({
                'success': True,
                'settings': all_settings
            })

        elif request.method == 'POST':
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

            data = request.get_json()
            if not data.get('key'):
                return jsonify({'success': False, 'error': 'Отсутствует key'}), 400

            success = db.update_setting(data['key'], data.get('value', ''))
            if success:
                return jsonify({'success': True, 'message': 'Настройка обновлена'})
            return jsonify({'success': False, 'error': 'Ошибка обновления'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/bulk', methods=['POST'])
def bulk_update_settings():
    """Массовое обновление настроек"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Требуется JSON'}), 400

        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({'success': False, 'error': 'Некорректный формат данных'}), 400

        updated = 0
        for key, value in data.items():
            if db.update_setting(key, str(value)):
                updated += 1

        return jsonify({
            'success': True,
            'message': f'Обновлено {updated} настроек',
            'updated': updated
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

if __name__ == '__main__':
    print("🚀 Запуск CRM Автосервиса...")
    app.run(debug=True, port=5000)