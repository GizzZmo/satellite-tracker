# backend/run_scheduler.pyrun_scheduler.py

from app.scheduler import initialize_scheduler
from app.models import init_db
import logging

if __name__ == "__main__":
    logging.info("Initialiserer database...")
    init_db()  # Sikrer at databasen og tabellene eksisterer
    
    logging.info("Starter scheduler-prosessen...")
    scheduler = initialize_scheduler()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stanset.")

