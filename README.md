# Satellittsporing og Visualiseringssystem

Dette prosjektet er et komplett system for sanntidssporing og 3D-visualisering av satellitter i bane rundt jorden. Det er bygget på en tre-lags arkitektur som beskrevet i den tekniske blåpausen.ArkitekturoversiktBackend: En Python-applikasjon bygget med FastAPI.Datainnhentingstjeneste: En planlagt prosess (scheduler) som henter satellittkatalog (SATCAT) og banedata (OMM) fra Space-Track.org.Propagerings- og API-tjeneste: En FastAPI-server som: Leser de siste banedataene fra en lokal database.Bruker sgp4-biblioteket til å beregne satellittenes nåværende posisjon. Strømmer posisjonsdata i sanntid til frontend-klienter via WebSockets. Tilbyr et REST API for å hente beregnede banespor.Frontend: En web-applikasjon bygget med ren HTML, CSS og JavaScript.Bruker CesiumJS for å rendere en interaktiv 3D-globus.Kobler til backend via WebSockets for å motta og visualisere satellittposisjoner i sanntid.Implementerer brukergrensesnitt for søk, filtrering og visning av detaljert informasjon.Oppsett og KjøringForutsetningerPython 3.8+En konto på Space-Track.org for å få tilgang til API-et.En gratis Cesium Ion-tilgangsnøkkel fra cesium.com for høyoppløselige kartlag.

satellite-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── data_fetcher.py   # Henter data fra Space-Track.org
│   │   ├── main.py           # FastAPI-app, WebSocket og API-endepunkter
│   │   ├── models.py         # SQLAlchemy-databasemodeller
│   │   └── scheduler.py      # APScheduler for planlagt datainnhenting
│   ├── run_scheduler.py      # Skript for å starte scheduler-prosessen
│   └── requirements.txt      # Python-avhengigheter
│
├── frontend/
│   ├── index.html            # Hovedsiden med Cesium-container
│   ├── main.js               # JavaScript-logikk for Cesium og UI
│   └── style.css             # CSS for brukergrensesnitt
│
└── README.md                 # Prosjektdokumentasjon

### 1. Backend Oppsetta. Naviger til backend-mappen:

        cd backend
   
### b. Opprett et virtuelt miljø og aktiver det:

       python -m venv venv
       source venv/bin/activate

# På Windows: 

        venv\Scripts\activate

### c. Installer avhengigheter:

        pip install -r requirements.txt

### d. Konfigurer miljøvariabler:Opprett en .env-fil i backend-mappen og legg til din Space-Track-legitimasjon. IKKE hardkode dette i koden.SPACETRACK_USERNAME="ditt-brukernavn"
SPACETRACK_PASSWORD="ditt-passord"
Merk: main.py er satt opp for å laste disse, men for produksjon bør en sikrere metode som HashiCorp Vault eller en skytjeneste for hemmeligheter brukes.e. Initialiser databasen:Første gang du kjører applikasjonen, vil databasen (database.db) bli opprettet.

### f. Kjør datainnhenteren (Scheduler):Denne prosessen må kjøres separat for å kontinuerlig hente data. Den vil først kjøre en full henting og deretter følge den planlagte timeplanen.python run_scheduler.py
### g. Kjør API-serveren:Åpne en ny terminal, aktiver det virtuelle miljøet, og start FastAPI-serveren.uvicorn app.main:app --reload
Serveren vil nå kjøre på http://127.0.0.1:8000.2. Frontend Oppsetta. Legg inn din Cesium Ion-nøkkel:Åpne frontend/main.js og erstatt 'DIN_CESIUM_ION_NØKKEL_HER' med din faktiske nøkkel.b. Åpne index.html i en nettleser:Du kan enten åpne filen direkte, eller for best resultat, serve den via en enkel lokal webserver. 

Hvis du har Python installert:cd frontend

    python -m http.server
Gå deretter til http://localhost:8000 i nettleseren din.FunksjonalitetSanntidsvisualisering: Se satellitter bevege seg over 3D-globusen.Søk og Filtrer: Bruk søkefeltet til å filtrere satellitter etter navn eller NORAD ID.Interaktiv InfoBox: Klikk på en satellitt for å se detaljert informasjon.Dynamiske Banespor: Når du klikker på en satellitt, hentes og vises dens fremtidige bane for de neste 90 minuttene.
