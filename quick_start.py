# quick_start.py
import subprocess
import sys
import os


def install_requirements():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Зависимости установлены")
    except Exception as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        print("Попробуйте установить вручную:")
        print("pip install Flask==2.3.3")


def create_test_data():
    """Создание тестовых данных"""
    print("\n🛠️  Создание тестовой базы данных...")
    try:
        from create_test_db import create_test_database, copy_to_main_db
        create_test_database('autoservice_test.db')
        copy_to_main_db()
        print("✅ Тестовые данные созданы")
    except Exception as e:
        print(f"❌ Ошибка создания тестовых данных: {e}")


def run_application():
    """Запуск приложения"""
    print("\n🚀 Запуск приложения...")
    print("Откройте в браузере: http://localhost:5000")
    print("Для остановки нажмите Ctrl+C\n")

    try:
        subprocess.check_call([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n🛑 Приложение остановлено")
    except Exception as e:
        print(f"❌ Ошибка запуска приложения: {e}")


def main():
    """Главная функция"""
    print("=" * 60)
    print("⚡ БЫСТРЫЙ СТАРТ CRM АВТОСЕРВИСА")
    print("=" * 60)

    # Проверяем наличие requirements.txt
    if not os.path.exists('requirements.txt'):
        print("📝 Создание requirements.txt...")
        with open('requirements.txt', 'w') as f:
            f.write("Flask==2.3.3\n")
        print("✅ requirements.txt создан")

    # Устанавливаем зависимости
    install_requirements()

    # Создаем тестовые данные
    create_test_data()

    # Запускаем приложение
    run_application()


if __name__ == '__main__':
    main()