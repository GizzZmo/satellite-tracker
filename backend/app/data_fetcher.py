# backend/app/data_fetcher.py

import requests
from sqlalchemy.orm import Session
from . import models
import logging

# Konfigurerer logging for å se status og feil
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URL-er for Space-Track API
SPACETRACK_URL = "https://www.space-track.org"
LOGIN_URL = f"{SPACETRACK_URL}/ajaxauth/login"
SATCAT_URL = f"{SPACETRACK_URL}/basicspacedata/query/class/satcat/CURRENT/Y/orderby/NORAD_CAT_ID/format/json"
GP_URL = f"{SPACETRACK_URL}/basicspacedata/query/class/gp/CURRENT/Y/orderby/NORAD_CAT_ID/format/json"

class SpaceTrackClient:
    """
    Klient for å håndtere autentisering og datainnhenting fra Space-Track.org.
    """
    def __init__(self, identity, password):
        self.identity = identity
        self.password = password
        self.session = requests.Session()

    def login(self):
        """Logger inn på Space-Track og beholder sesjonen."""
        logging.info("Logger inn på Space-Track.org...")
        payload = {'identity': self.identity, 'password': self.password}
        try:
            response = self.session.post(LOGIN_URL, data=payload)
            response.raise_for_status()  # Kaster en exception for dårlige responser (4xx eller 5xx)
            logging.info("Vellykket innlogging på Space-Track.org.")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Innlogging feilet: {e}")
            return False

    def fetch_data(self, url):
        """Henter data fra en gitt URL ved hjelp av den autentiserte sesjonen."""
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Kunne ikke hente data fra {url}: {e}")
            return None
        except ValueError: # Håndterer JSON-dekodingsfeil
            logging.error(f"Kunne ikke dekode JSON fra {url}")
            return None

    def fetch_and_update_satcat(self, db: Session):
        """Henter den nyeste satellittkatalogen og oppdaterer databasen."""
        logging.info("Starter henting av SATCAT...")
        data = self.fetch_data(SATCAT_URL)
        if not data:
            logging.warning("Ingen SATCAT-data hentet.")
            return

        logging.info(f"Hentet {len(data)} oppføringer fra SATCAT.")
        for sat in data:
            # Sjekker om satellitten allerede eksisterer
            db_sat = db.query(models.SatelliteCatalog).filter(models.SatelliteCatalog.norad_cat_id == sat['NORAD_CAT_ID']).first()
            if not db_sat:
                # Oppretter ny oppføring hvis den ikke finnes
                new_sat = models.SatelliteCatalog(
                    norad_cat_id=int(sat['NORAD_CAT_ID']),
                    object_name=sat.get('OBJECT_NAME', 'N/A'),
                    intldes=sat.get('INTLDES', 'N/A'),
                    country=sat.get('COUNTRY', 'N/A'),
                    launch_date=sat.get('LAUNCH_DATE', 'N/A'),
                    object_type=sat.get('OBJECT_TYPE', 'N/A')
                )
                db.add(new_sat)
        db.commit()
        logging.info("SATCAT-database oppdatert.")

    def fetch_and_update_gp_data(self, db: Session):
        """Henter de nyeste GP-dataene (OMM) og oppdaterer databasen."""
        logging.info("Starter henting av GP-data...")
        data = self.fetch_data(GP_URL)
        if not data:
            logging.warning("Ingen GP-data hentet.")
            return

        logging.info(f"Hentet {len(data)} GP-oppføringer.")
        # Sletter gamle GP-data for å kun beholde de nyeste
        db.query(models.GeneralPerturbations).delete()

        for gp in data:
            # Sjekker om den tilhørende satellitten finnes i katalogen
            sat_exists = db.query(models.SatelliteCatalog).filter(models.SatelliteCatalog.norad_cat_id == gp['NORAD_CAT_ID']).first()
            if sat_exists and gp.get('MEAN_MOTION') is not None:
                new_gp = models.GeneralPerturbations(
                    norad_cat_id=int(gp['NORAD_CAT_ID']),
                    epoch=gp.get('EPOCH'),
                    mean_motion=float(gp['MEAN_MOTION']),
                    eccentricity=float(gp['ECCENTRICITY']),
                    inclination=float(gp['INCLINATION']),
                    ra_of_asc_node=float(gp['RA_OF_ASC_NODE']),
                    arg_of_pericenter=float(gp['ARG_OF_PERICENTER']),
                    mean_anomaly=float(gp['MEAN_ANOMALY']),
                    bstar=float(gp.get('BSTAR', 0.0)),
                    rev_at_epoch=int(gp['REV_AT_EPOCH'])
                )
                db.add(new_gp)
        db.commit()
        logging.info("GP-database oppdatert.")

