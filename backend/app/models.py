# backend/app/models.py

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
import os

# Definerer database-URL. Bruker SQLite for enkelhetens skyld.
DATABASE_URL = "sqlite:///./database.db"

# Oppretter en baseklasse for deklarative modeller
Base = declarative_base()

# Definerer modellen for satellittkatalogen (SATCAT)
class SatelliteCatalog(Base):
    __tablename__ = "satellite_catalog"

    # Definerer kolonner for tabellen
    norad_cat_id = Column(Integer, primary_key=True, index=True)
    object_name = Column(String, index=True)
    intldes = Column(String) # Internasjonal designator
    country = Column(String)
    launch_date = Column(String)
    object_type = Column(String)
    
    # Etablerer en en-til-mange-relasjon til GeneralPerturbations
    # En satellitt kan ha mange GP-datasett over tid
    gp_data = relationship("GeneralPerturbations", back_populates="satellite")

# Definerer modellen for General Perturbations (GP) data, som er baneelementene fra OMM
class GeneralPerturbations(Base):
    __tablename__ = "general_perturbations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Fremmednøkkel som kobler til SatelliteCatalog
    norad_cat_id = Column(Integer, ForeignKey("satellite_catalog.norad_cat_id"))
    
    # Tidspunktet (epoch) for når disse baneelementene var gyldige
    epoch = Column(String) 
    
    # Klassiske Keplerianske baneelementer
    mean_motion = Column(Float)
    eccentricity = Column(Float)
    inclination = Column(Float)
    ra_of_asc_node = Column(Float) # Rektascensjon for oppstigende knute
    arg_of_pericenter = Column(Float) # Perigeumsargument
    mean_anomaly = Column(Float)
    
    # Andre viktige parametere fra OMM/TLE
    bstar = Column(Float) # B* drag term
    rev_at_epoch = Column(Integer) # Omløpsnummer ved epoch
    
    # Tidspunkt for når dataene ble hentet og lagret
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    # Etablerer en mange-til-en-relasjon tilbake til SatelliteCatalog
    satellite = relationship("SatelliteCatalog", back_populates="gp_data")

# Oppretter en database-motor
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Oppretter en sesjonsklasse som vil bli brukt til å interagere med databasen
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Funksjon for å opprette alle tabellene i databasen
def init_db():
    Base.metadata.create_all(bind=engine)

# Funksjon for å få en databasesesjon
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
