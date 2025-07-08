# backend/app/main.py

import asyncio
import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from . import models, get_db
from sgp4.api import Satrec, jday
from pyproj import Transformer, CRS
import logging

# Konfigurerer logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialiserer FastAPI-applikasjonen
app = FastAPI()

# Oppretter transformator for koordinatsystemer
# ECEF (Earth-Centered, Earth-Fixed) -> Geodetic (Latitude, Longitude, Altitude)
# EPSG:4978 er ECEF, EPSG:4979 er Geodetic 3D
ecef = CRS("EPSG:4978")
geodetic = CRS("EPSG:4979")
transformer = Transformer.from_crs(ecef, geodetic, always_xy=True)

class ConnectionManager:
    """Håndterer aktive WebSocket-tilkoblinger."""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
            
    async def broadcast_json(self, data: list):
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

def propagate_satellites(db: Session):
    """Henter satellitter fra DB, propagerer deres posisjon og returnerer en liste."""
    
    # Henter alle satellitter som har gyldige GP-data
    sats_with_gp = db.query(models.SatelliteCatalog).join(models.GeneralPerturbations).all()
    
    # Få nåværende tid i UTC
    now = datetime.datetime.utcnow()
    # Konverter til Julian Date, som SGP4 trenger
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)

    results = []
    for sat in sats_with_gp:
        # Bruker det siste GP-datasettet (antatt sortert eller det eneste)
        gp = sat.gp_data[-1]
        
        # Oppretter et Satrec-objekt fra baneelementene
        satellite = Satrec()
        satellite.sgp4init(
            models.WGS84,           # Gravitasjonskonstant
            'i',                    # Initialiseringsmodus ('i' for improved)
            int(sat.norad_cat_id),  # Satellittnummer
            jd + fr - 2433281.5,    # Epoch i dager fra 1949-12-31
            gp.bstar,
            gp.mean_motion,
            gp.eccentricity,
            gp.inclination,
            gp.ra_of_asc_node,
            gp.arg_of_pericenter,
            gp.mean_anomaly
        )

        # Propagerer satellittens posisjon til nåværende tid
        error, position, velocity = satellite.sgp4(jd, fr)

        # Sjekker for propageringsfeil
        if error == 0:
            # SGP4 returnerer posisjon i TEME-koordinatsystemet i km.
            # Vi konverterer til meter for pyproj.
            pos_ecef = [p * 1000 for p in position]

            # Transformer fra ECEF til Geodetic (lon, lat, alt)
            lon, lat, alt = transformer.transform(pos_ecef[0], pos_ecef[1], pos_ecef[2])
            
            results.append({
                "norad_id": sat.norad_cat_id,
                "name": sat.object_name,
                "lon": lon,
                "lat": lat,
                "alt": alt, # Høyde i meter
            })
    return results

async def propagation_loop():
    """En evig løkke som propagerer satellitter og kringkaster posisjonene."""
    db = next(get_db())
    while True:
        try:
            satellite_positions = propagate_satellites(db)
            if satellite_positions:
                await manager.broadcast_json(satellite_positions)
            # Venter i 1 sekund før neste oppdatering
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Feil i propageringsløkken: {e}")
            # Venter lenger ved feil for å unngå raske feil-sykluser
            await asyncio.sleep(10)


@app.on_event("startup")
async def startup_event():
    """Starter bakgrunnsoppgaven for propagering når serveren starter."""
    logging.info("Server starter... Oppretter propageringsløkke.")
    asyncio.create_task(propagation_loop())


@app.websocket("/ws/satellites")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket-endepunkt for å strømme sanntids satellittposisjoner."""
    await manager.connect(websocket)
    logging.info(f"Ny klient koblet til: {websocket.client}")
    try:
        while True:
            # Holder tilkoblingen åpen
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info(f"Klient koblet fra: {websocket.client}")

@app.get("/api/orbit_track/{norad_id}")
def get_orbit_track(norad_id: int, db: Session = Depends(get_db)):
    """API-endepunkt for å hente et beregnet banespor for en gitt satellitt."""
    # Finner satellitten og dens GP-data
    gp = db.query(models.GeneralPerturbations).filter_by(norad_cat_id=norad_id).first()
    if not gp:
        return {"error": "Satellitt ikke funnet"}

    satellite = Satrec()
    # Initialiserer Satrec-objektet
    # ... (samme initialisering som i propagate_satellites) ...

    track = []
    start_time = datetime.datetime.utcnow()
    # Beregner posisjon for de neste 90 minuttene, med 60 sekunders intervall
    for i in range(91):
        time_offset = start_time + datetime.timedelta(minutes=i)
        jd, fr = jday(time_offset.year, time_offset.month, time_offset.day, time_offset.hour, time_offset.minute, time_offset.second)
        
        error, position, _ = satellite.sgp4(jd, fr)
        if error == 0:
            pos_ecef = [p * 1000 for p in position]
            lon, lat, alt = transformer.transform(pos_ecef[0], pos_ecef[1], pos_ecef[2])
            track.append({
                "time": time_offset.isoformat() + "Z",
                "lon": lon,
                "lat": lat,
                "alt": alt
            })
            
    return track

