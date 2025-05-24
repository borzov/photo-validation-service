#!/usr/bin/env python3
"""
Скрипт для миграции данных с SQLite на PostgreSQL.
Запуск: python scripts/migrate_to_postgresql.py
"""
import sys
import os

# Добавляем корень проекта в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.migration_utils import migrate_to_postgresql
from app.core.logging import get_logger

logger = get_logger(__name__)

def main():
    """Основная функция скрипта миграции."""
    print("Начинаем миграцию данных с SQLite на PostgreSQL...")
    
    try:
        success = migrate_to_postgresql()
        
        if success:
            print("✅ Миграция завершена успешно!")
            print("🗂️  SQLite файл перемещен в резервную копию")
            print("🚀 Теперь система использует только PostgreSQL")
        else:
            print("❌ Миграция не удалась. Проверьте логи для деталей.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Критическая ошибка при миграции: {e}")
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 