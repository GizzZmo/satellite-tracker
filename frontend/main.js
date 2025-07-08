// frontend/main.js

// --- Konfigurasjon ---
// ERSTATT MED DIN EGEN CESIUM ION NØKKEL
Cesium.Ion.defaultAccessToken = 'DIN_CESIUM_ION_NØKKEL_HER'; 
const WEBSOCKET_URL = "ws://127.0.0.1:8000/ws/satellites";
const API_URL = "http://127.0.0.1:8000/api";

// --- Initialisering ---
// Initialiserer Cesium Viewer med utvalgte innstillinger for et renere grensesnitt
const viewer = new Cesium.Viewer('cesiumContainer', {
    animation: false, // Skjuler animasjonswidget
    baseLayerPicker: false, // Skjuler kartlagsvelger
    fullscreenButton: false, // Skjuler fullskjermsknapp
    geocoder: false, // Skjuler geocoder (adressesøk)
    homeButton: false, // Skjuler "gå til hjem"-knapp
    infoBox: true, // Viser infoboks ved klikk
    sceneModePicker: false, // Skjuler 2D/3D-velger
    selectionIndicator: false, // Skjuler grønn boks rundt valgte objekter
    timeline: false, // Skjuler tidslinje
    navigationHelpButton: false, // Skjuler hjelpeknapp
    terrainProvider: Cesium.createWorldTerrain() // Legger til terrengdata
});

// Fjerner Cesium-logoen for et renere utseende
viewer.cesiumWidget.creditContainer.style.display = "none";

// --- Tilstandsvariabler ---
// Bruker et Map for effektiv oppslag, oppretting og oppdatering av satellitt-entiteter
const satelliteEntities = new Map();
let currentOrbitTrack = null; // Holder styr på den nåværende viste banen

// --- UI-elementer ---
const searchInput = document.getElementById('searchInput');
const connectionStatus = document.getElementById('connection-status');

// --- WebSocket Håndtering ---
function setupWebSocket() {
    const socket = new WebSocket(WEBSOCKET_URL);

    socket.onopen = () => {
        console.log("Koblet til WebSocket-server.");
        updateConnectionStatus(true);
    };

    socket.onmessage = (event) => {
        const satellites = JSON.parse(event.data);
        updateSatellites(satellites);
    };

    socket.onclose = () => {
        console.warn("WebSocket-tilkobling lukket. Prøver å koble til på nytt om 5 sekunder.");
        updateConnectionStatus(false);
        // Enkel mekanisme for å prøve å koble til på nytt
        setTimeout(setupWebSocket, 5000);
    };

    socket.onerror = (error) => {
        console.error("WebSocket-feil:", error);
        updateConnectionStatus(false);
        socket.close(); // Utløser onclose som vil prøve å koble til på nytt
    };
}

function updateConnectionStatus(isConnected) {
    if (isConnected) {
        connectionStatus.textContent = '● Tilkoblet';
        connectionStatus.className = 'connected';
    } else {
        connectionStatus.textContent = '● Frakoblet';
        connectionStatus.className = 'disconnected';
    }
}

// --- Satellitt- og Visualiseringslogikk ---
function updateSatellites(satellites) {
    const filterText = searchInput.value.toLowerCase();

    satellites.forEach(sat => {
        const position = Cesium.Cartesian3.fromDegrees(sat.lon, sat.lat, sat.alt);
        let entity = satelliteEntities.get(sat.norad_id);

        if (entity) {
            // Oppdater posisjonen til en eksisterende entitet
            entity.position = position;
        } else {
            // Opprett en ny entitet hvis den ikke finnes
            entity = viewer.entities.add({
                id: sat.norad_id,
                position: position,
                point: {
                    pixelSize: 5,
                    color: Cesium.Color.ORANGERED,
                    outlineColor: Cesium.Color.WHITE,
                    outlineWidth: 1
                },
                label: {
                    text: sat.name,
                    font: '12pt sans-serif',
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    outlineWidth: 2,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -9),
                    distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0.0, 1.5e7) // Vis kun når man er zoomet inn
                },
                // Lagrer metadata direkte på entiteten for senere bruk
                properties: {
                    name: sat.name,
                    norad_id: sat.norad_id
                }
            });
            satelliteEntities.set(sat.norad_id, entity);
        }

        // Oppdater synligheten basert på søkefilteret
        const nameMatch = sat.name.toLowerCase().includes(filterText);
        const idMatch = sat.norad_id.toString().includes(filterText);
        entity.show = filterText === '' || nameMatch || idMatch;
    });
}

async function showOrbitTrack(noradId) {
    // Fjerner en eventuell eksisterende bane
    if (currentOrbitTrack) {
        viewer.entities.remove(currentOrbitTrack);
        currentOrbitTrack = null;
    }

    try {
        const response = await fetch(`${API_URL}/orbit_track/${noradId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const trackData = await response.json();

        if (trackData.error) throw new Error(trackData.error);
        
        // Oppretter en SampledPositionProperty for å animere banen
        const positionProperty = new Cesium.SampledPositionProperty();
        trackData.forEach(point => {
            const time = Cesium.JulianDate.fromIso8601(point.time);
            const position = Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.alt);
            positionProperty.addSample(time, position);
        });

        // Oppretter en entitet for å vise banen
        currentOrbitTrack = viewer.entities.add({
            id: `orbit_track_${noradId}`,
            availability: new Cesium.TimeIntervalCollection([new Cesium.TimeInterval({
                start: Cesium.JulianDate.fromIso8601(trackData[0].time),
                stop: Cesium.JulianDate.fromIso8601(trackData[trackData.length - 1].time)
            })]),
            position: positionProperty,
            path: {
                resolution: 120,
                material: new Cesium.PolylineGlowMaterialProperty({
                    glowPower: 0.1,
                    color: Cesium.Color.YELLOW
                }),
                width: 2,
                trailTime: 45 * 60, // Viser 45 minutter av sporet bak
                leadTime: 45 * 60 // Viser 45 minutter av sporet foran
            }
        });

    } catch (error) {
        console.error(`Kunne ikke hente banespor for ${noradId}:`, error);
    }
}

// --- Event Listeners ---
// Lytter etter endringer i søkefeltet for å filtrere i sanntid
searchInput.addEventListener('input', () => {
    const filterText = searchInput.value.toLowerCase();
    satelliteEntities.forEach((entity, norad_id) => {
        const name = entity.properties.name.getValue().toLowerCase();
        const id = norad_id.toString();
        entity.show = filterText === '' || name.includes(filterText) || id.includes(filterText);
    });
});

// Lytter etter klikk på entiteter
viewer.selectedEntityChanged.addEventListener((selectedEntity) => {
    if (Cesium.defined(selectedEntity) && selectedEntity.id) {
        // Formaterer beskrivelsen for infoboksen
        const props = selectedEntity.properties;
        selectedEntity.description = `
            <div style="padding:10px; font-family: sans-serif; color: white;">
                <strong>Navn:</strong> ${props.name.getValue()}<br>
                <strong>NORAD ID:</strong> ${props.norad_id.getValue()}
            </div>`;
        
        // Henter og viser banesporet for den valgte satellitten
        showOrbitTrack(selectedEntity.id);
    } else {
        // Fjerner banesporet når ingenting er valgt
        if (currentOrbitTrack) {
            viewer.entities.remove(currentOrbitTrack);
            currentOrbitTrack = null;
        }
    }
});


// --- Oppstart ---
// Starter WebSocket-tilkoblingen når siden er lastet
setupWebSocket();
