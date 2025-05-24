"""
Утилиты для миграции базы данных с SQLite на PostgreSQL.
"""
import os
import sqlite3
import psycopg2
from sqlalchemy import create_engine
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class DatabaseMigrationUtil:
    """Утилита для миграции данных с SQLite на PostgreSQL."""
    
    def __init__(self):
        self.sqlite_path = "photo_validation.db"
        self.postgres_url = settings.DATABASE_URL
    
    def check_sqlite_exists(self) -> bool:
        """Проверяет наличие файла SQLite."""
        return os.path.exists(self.sqlite_path)
    
    def migrate_data(self) -> bool:
        """Мигрирует данные из SQLite в PostgreSQL."""
        if not self.check_sqlite_exists():
            logger.info("SQLite файл не найден. Миграция не требуется.")
            return True
        
        try:
            # Подключение к SQLite
            sqlite_conn = sqlite3.connect(self.sqlite_path)
            sqlite_cursor = sqlite_conn.cursor()
            
            # Подключение к PostgreSQL
            postgres_engine = create_engine(self.postgres_url)
            
            # Получаем список таблиц из SQLite
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = sqlite_cursor.fetchall()
            
            migrated_records = 0
            
            for table in tables:
                table_name = table[0]
                if table_name.startswith('sqlite_'):
                    continue
                
                logger.info(f"Мигрируем таблицу: {table_name}")
                
                # Получаем данные из SQLite
                sqlite_cursor.execute(f"SELECT * FROM {table_name}")
                rows = sqlite_cursor.fetchall()
                
                # Получаем названия колонок
                sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [column[1] for column in sqlite_cursor.fetchall()]
                
                if rows:
                    # Формируем SQL для вставки в PostgreSQL
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_str = ', '.join(columns)
                    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                    
                    # Выполняем вставку
                    with postgres_engine.connect() as postgres_conn:
                        for row in rows:
                            try:
                                postgres_conn.execute(insert_sql, row)
                                migrated_records += 1
                            except Exception as row_error:
                                logger.warning(f"Ошибка при вставке записи в {table_name}: {row_error}")
                                continue
            
            sqlite_conn.close()
            
            logger.info(f"Миграция завершена. Перенесено записей: {migrated_records}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при миграции данных: {e}")
            return False
    
    def cleanup_sqlite(self) -> bool:
        """Удаляет файл SQLite после успешной миграции."""
        try:
            if self.check_sqlite_exists():
                # Создаем резервную копию
                backup_path = f"{self.sqlite_path}.backup"
                os.rename(self.sqlite_path, backup_path)
                logger.info(f"SQLite файл перемещен в резервную копию: {backup_path}")
                return True
            return True
        except Exception as e:
            logger.error(f"Ошибка при очистке SQLite файла: {e}")
            return False

def migrate_to_postgresql():
    """Функция для выполнения полной миграции."""
    migration_util = DatabaseMigrationUtil()
    
    if migration_util.migrate_data():
        if migration_util.cleanup_sqlite():
            logger.info("Миграция с SQLite на PostgreSQL завершена успешно")
            return True
    
    logger.error("Миграция не удалась")
    return False 