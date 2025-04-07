from firestore import db
from default_schedule import default_schedule
import firebase_admin
from firebase_admin import credentials, firestore

# Створення розкладу за замовчуванням
def create_default_schedule(telegram_id):
    schedule_ref = db.collection("TG_USERS").document(str(telegram_id))
    schedule_ref.set({
        "schedule": default_schedule,
        "telegram_id": telegram_id,
        "created_at": firestore.SERVER_TIMESTAMP
    })