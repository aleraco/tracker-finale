from flask import Flask, render_template
import requests, time
from datetime import datetime

app = Flask(__name__)

# ---------------- UTIL ----------------
def format_epoch(epoch_time):
    try:
        return datetime.fromtimestamp(epoch_time).strftime("%H:%M")
    except:
        return "N/D"
        
def normalize_flight(fn):
    return fn.replace(" ", "").upper()

def minuti_rimanenti(eta_epoch):
    try:
        if not eta_epoch:
            return None

        now = int(time.time())
        diff = int((eta_epoch - now) / 60)

        return diff
    except:
        return None
        

# ---------------- ARRIVALS LIST ----------------
@app.route("/")
def arrivals_list():
    url = "https://fligtradar24-data.p.rapidapi.com/v1/airports/arrivals"
    params = {"limit": "40", "page": "1", "code": "fco"}
    headers = {
        "x-rapidapi-key": "db837ae358msh61f8796d5b31c86p1931e4jsn4ccd24caeeaf",
        "x-rapidapi-host": "fligtradar24-data.p.rapidapi.com"
    }
   
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()

        arrivi_raw = (
            data.get("data", {})
                .get("airport", {})
                .get("pluginData", {})
                .get("schedule", {})
                .get("arrivals", {})
                .get("data", [])
        )

        arrivi = []

        for item in arrivi_raw:
            flight = item.get("flight") or {}
            identification = flight.get("identification") or {}
            airline = flight.get("airline") or {}
            airport = flight.get("airport") or {}
            owner = flight.get("owner") or {}
            status = flight.get("status") or {}
            time_data = flight.get("time") or {}

            flight_number = identification.get("number", {}).get("default")
            if not flight_number:
                continue

            flight_number = normalize_flight(flight_number)

            scheduled = time_data.get("scheduled", {}).get("arrival")
            real = time_data.get("real", {}).get("arrival")
            estimated = time_data.get("estimated", {}).get("arrival")
            other_eta = time_data.get("other", {}).get("eta")

            # ETA reale da usare per il countdown
            eta_epoch = other_eta or estimated or real or scheduled

            minuti = minuti_rimanenti(eta_epoch)
            if not isinstance(minuti, int):
                minuti = 0

            arrivi.append({
                "flight_number": flight_number,
                "compagnia": airline.get("name", "N/D"),
                "logo": owner.get("logo", ""),
                "provenienza": (
                    airport.get("origin", {})
                        .get("position", {})
                        .get("region", {})
                        .get("city", "N/D")
                ),
                "stato_testo": status.get("text", "N/D"),
                "colore": status.get("icon", "grey"),
                "orario_sched_arr": format_epoch(scheduled),
                "orario_real_arr": format_epoch(real),
                "terminal": (
                    airport.get("destination", {})
                        .get("info", {})
                        .get("terminal", "N/D")
                ),
                "gate": (
                    airport.get("destination", {})
                        .get("info", {})
                        .get("gate", "N/D")
                ),
                "minuti_mancanti": minuti
            })

        print(f"CARDS CREATE: {len(arrivi)}")
                
        return render_template("arrivals_list.html", arrivi=arrivi)

    except Exception as e:
        print("❌ ERRORE ARRIVI:", e)
        return render_template(
            "flight_error.html",
            messaggio="Impossibile recuperare gli arrivi."
        )
        
# ---------------- FLIGHT MAP ----------------
@app.route("/flight/<flight_number>")
def flight_map(flight_number):
    flight_number = normalize_flight(flight_number)

    url = "https://airlabs.co/api/v9/flights"
    params = {
        "api_key": "814d50a0-286e-4e5d-88b8-a993615c9bc3",
        "arr_iata": "FCO",
        "_fields": "flight_iata,lat,lng,dir,alt,status,dep_iata"
    }

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        flights = res.json().get("response", [])

        print("CERCO VOLO:", flight_number)

        volo = next(
            (f for f in flights if f.get("flight_iata") == flight_number),
            None
        )
    
        if not volo:
            raise ValueError(f"Volo {flight_number} non trovato su AirLabs")
        print("VOLO TROVATO:", volo)
        return render_template("flight-maps.html", volo=volo)
       
                
    except Exception as e:
        print("❌ ERRORE MAPPA:", e)
        return render_template(
            "flight_error.html",
            messaggio="Impossibile recuperare la posizione del volo."
        )


if __name__ == "__main__":
    app.run(debug=True)
