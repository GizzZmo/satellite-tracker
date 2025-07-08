# backend/app/scheduler.py

import os
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from .data_fetcher import SpaceTrackClient
from . import models, SessionLocal
import logging

# Laster miljøvariabler fra .env-filen
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(scheduler)s - %(levelname)s - %(message)s')

def run_satcat_update():
    """Jobb for å oppdatere SATCAT-data."""
    logging.info("--- Kjører planlagt SATCAT-oppdatering ---")
    db = SessionLocal()
    client = SpaceTrackClient(os.getenv("SPACETRACK_USERNAME"), os.getenv("SPACETRACK_PASSWORD"))
    if client.login():
        client.fetch_and_update_satcat(db)
    db.close()
    logging.info("--- Fullført SATCAT-oppdatering ---")

def run_gp_update():
    """Jobb for å oppdatere GP-data."""
    logging.info("--- Kjører planlagt GP-dataoppdatering ---")
    db = SessionLocal()
    client = SpaceTrackClient(os.getenv("SPACETRACK_USERNAME"), os.getenv("SPACETRACK_PASSWORD"))
    if client.login():
        client.fetch_and_update_gp_data(db)
    db.close()
    logging.info("--- Fullført GP-dataoppdatering ---")

def initialize_scheduler():
    """Initialiserer og konfigurerer APScheduler."""
    scheduler = BlockingScheduler(timezone="UTC")
    
    # Planlegger jobbene
    # Henter SATCAT en gang daglig kl. 18:00 UTC
    scheduler.add_job(run_satcat_update, 'cron', hour=18, minute=0)
    
    # Henter GP-data hver time
    scheduler.add_job(run_gp_update, 'interval', hours=1)
    
    logging.info("Scheduler initialisert. Jobber er lagt til.")
    logging.info("Kjører en initiell full datahenting nå...")
    
    # Kjører en initiell henting umiddelbart ved oppstart
    run_satcat_update()
    run_gp_update()
    
    return scheduler

