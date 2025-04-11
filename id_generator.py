# id_generator.py
import time

def generate_unique_id() -> int:
    """Генерує унікальний ID на основі часу в мілісекундах"""
    return int(time.time() * 1000)