from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from pathlib import Path
import pandas as pd
import joblib
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

app = Flask(__name__)
# Allow CORS origin override via env; defaults to all origins for local development.
CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})

BASE_DIR = Path(__file__).resolve().parent
lr_model = None
rf_clf = None
symptom_classifier = None
HOSPITALS = pd.DataFrame()


def load_backend_assets():
    global lr_model, rf_clf, symptom_classifier, HOSPITALS
    print("Loading models and hospital data...")

    data_path = BASE_DIR / "hospitals_data.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Required file missing: {data_path}")

    HOSPITALS = pd.read_csv(data_path)
    required_cols = {"name", "lat", "lon", "departments"}
    missing_cols = required_cols - set(HOSPITALS.columns)
    if missing_cols:
        raise ValueError(f"hospitals_data.csv is missing columns: {sorted(missing_cols)}")

    HOSPITALS["lat"] = pd.to_numeric(HOSPITALS["lat"], errors="coerce")
    HOSPITALS["lon"] = pd.to_numeric(HOSPITALS["lon"], errors="coerce")
    HOSPITALS = HOSPITALS.dropna(subset=["lat", "lon", "departments"]).copy()

    lr_path = BASE_DIR / "linear_regression_wait_time.pkl"
    rf_path = BASE_DIR / "random_forest_bed_clf.pkl"
    symptom_path = BASE_DIR / "symptom_classifier.pkl"

    if lr_path.exists():
        lr_model = joblib.load(lr_path)
    if rf_path.exists():
        rf_clf = joblib.load(rf_path)
    if symptom_path.exists():
        symptom_classifier = joblib.load(symptom_path)

    if symptom_classifier is None:
        print("Symptom model not found. Attempting fallback pipeline import...")
        try:
            from train_nlp_model import pipeline
            symptom_classifier = pipeline
            print("Fallback NLP pipeline loaded.")
        except Exception as e:
            print(f"Fallback NLP pipeline unavailable: {e}")

    print("Backend assets loaded.")


try:
    load_backend_assets()
except Exception as e:
    print(f"Startup warning: {e}")

# Initialize geolocator
geolocator = Nominatim(user_agent="hospital-recommendation-system")

def geocode_location(area_name):
    """Convert an area name in Chennai to latitude/longitude."""
    search_key = str(area_name).lower().strip()
    KNOWN_LOCATIONS = {
        "chennai": (13.0827, 80.2707),
        "egmore": (13.0732, 80.2609),
        "nungambakkam": (13.06, 80.243),
        "guindy": (13.0067, 80.2206),
        "adyar": (13.0012, 80.2565),
        "anna nagar": (13.085, 80.2101),
        "t nagar": (13.0418, 80.2341),
        "t. nagar": (13.0418, 80.2341),
        "velachery": (12.9815, 80.218),
        "tambaram": (12.9249, 80.1),
        "mylapore": (13.0368, 80.2676),
        "omr": (12.9038, 80.2267),
        "ecr": (12.9003, 80.2565),
        "perambur": (13.1091, 80.2464),
        "poonamallee": (13.0473, 80.0945),
        "vadapalani": (13.05, 80.2121),
        "ambattur": (13.0983, 80.158),
        "avadi": (13.1148, 80.0962),
        "porur": (13.0356, 80.1573),
        "chromepet": (12.9516, 80.1448),
        "sholinganallur": (12.901, 80.2279),
        "thoraipakkam": (12.9246, 80.2272),
        "perungudi": (12.9569, 80.2467),
        "chetpet": (13.0726, 80.2413),
        "shenoy nagar": (13.0874, 80.2179),
        "villivakkam": (13.1074, 80.2161),
        "kodambakkam": (13.049, 80.2199),
        "ashok nagar": (13.0288, 80.2158),
        "valasaravakkam": (13.0477, 80.1742),
        "chembarambakkam": (13.0222, 80.102),
        "mangadu": (13.0508, 80.0836),
        "manapakkam": (12.9903, 80.1893),
        "pallavaram": (12.9673, 80.1511),
        "perungalathur": (12.9015, 80.0839),
        "selaiyur": (12.9145, 80.1373),
        "medavakkam": (12.9171, 80.1988),
        "sholavaram": (13.1779, 80.2239),
        "madhavaram": (13.1485, 80.2313),
        "manali": (13.1645, 80.2588),
        "tiruvottiyur": (13.1615, 80.3038),
        "royapettah": (13.0554, 80.2681),
        "triplicane": (13.058, 80.28),
        "basin bridge": (13.0975, 80.2775),
        "purasaiwalkam": (13.0925, 80.254),
        "kilpauk": (13.0873, 80.242),
        "pulianthope": (13.1003, 80.2713),
        "sowcarpet": (13.093, 80.277),
        "george town": (13.0902, 80.2858),
        "tondiarpet": (13.1218, 80.2934),
        "thiruvanmiyur": (12.9829, 80.2594),
        "besant nagar": (13.0003, 80.2669),
        "kotturpuram": (13.0215, 80.2524),
        "kottivakkam": (12.9519, 80.2524),
        "palavakkam": (12.9421, 80.2548),
        "injambakkam": (12.9246, 80.2603),
        "kanathur": (12.9148, 80.2585),
        "muttukadu": (12.8726, 80.2404),
        "kovalam": (12.838, 80.2417),
        "mahabalipuram": (12.621, 80.1928),
        "siruseri": (12.8793, 80.2201),
        "padur": (12.8536, 80.2146),
        "kelambakkam": (12.8353, 80.2278),
        "karapakkam": (12.9013, 80.2256),
        "sithalapakkam": (12.8859, 80.1775),
        "guduvanchery": (12.8456, 80.0683),
        "maraimalai nagar": (12.7782, 80.0259),
        "singaperumal koil": (12.7783, 80.0),
        "vandalur": (12.8858, 80.0748),
        "anakaputhur": (13.0061, 80.1476),
        "peerkankaranai": (12.9169, 80.1595),
        "pudupakkam": (12.8671, 80.2028),
        "kattankulathur": (12.8231, 80.0444),
        "sozhinganallur": (12.8989, 80.2124),
        "semmancheri": (12.8814, 80.2225),
        "navalur": (12.8465, 80.2277),
        "kazhipattur": (12.8388, 80.2192),
        "vilankurichi": (11.0433, 77.0199),
        "kalapatti": (11.0641, 77.0465),
        "kancheepuram": (12.8342, 79.7036),
        "chengalpattu": (12.6919, 79.974),
        "madurantakam": (12.4942, 79.898),
        "uthiramerur": (12.7291, 79.7441),
        "sriperumbudur": (12.9694, 79.9484),
        "walajabad": (12.8085, 79.8408),
        "kundrathur": (13.0049, 80.1127),
        "tiruvallur": (13.1442, 79.9088),
        "ponneri": (13.3412, 80.1969),
        "ennore": (13.2191, 80.3253),
        "redhills": (13.1882, 80.1909),
        "tiruttani": (13.1857, 79.6165),
        "gummidipundi": (13.4082, 80.1092),
        "arakonam": (13.0796, 79.6709),
        "nemam": (13.2228, 80.1403),
        "vellore": (12.9239, 79.1326),
        "katpadi": (12.9717, 79.1497),
        "ranipet": (12.9313, 79.3329),
        "arcot": (12.9063, 79.3196),
        "ambur": (12.7882, 78.7177),
        "vaniyambadi": (12.6969, 78.6186),
        "walajapet": (12.9271, 79.3682),
        "sholinghur": (13.1127, 79.4221),
        "tiruvannamalai": (12.2253, 79.0747),
        "polur": (12.1631, 79.1468),
        "arni": (12.6718, 79.2888),
        "cheyyar": (12.6624, 79.5379),
        "vandavasi": (12.5001, 79.6302),
        "cuddalore": (11.7447, 79.768),
        "chidambaram": (11.3993, 79.6915),
        "neyveli": (11.6083, 79.5014),
        "pannaikuppam": (11.7447, 79.78),
        "virudhachalam": (11.5215, 79.3269),
        "kallakurichi": (11.7381, 78.957),
        "panruti": (11.7749, 79.5701),
        "villupuram": (11.9394, 79.4918),
        "gingi": (12.2531, 79.4168),
        "pondicherry": (11.9388, 79.8293),
        "puducherry": (11.9388, 79.8293),
        "tindivanam": (12.2344, 79.6527),
        "salem": (11.6643, 78.146),
        "mettur": (11.787, 77.8005),
        "omalur": (11.7319, 77.9982),
        "attur": (11.5959, 78.6019),
        "yercaud": (11.7745, 78.2092),
        "edappadi": (11.597, 78.0987),
        "sankari": (11.5771, 77.9164),
        "namakkal": (11.2213, 78.1674),
        "rasipuram": (11.457, 78.1757),
        "tiruchengode": (11.3886, 77.8951),
        "kolli hills": (11.3218, 78.364),
        "dharmapuri": (12.1211, 78.1582),
        "pennagaram": (12.1349, 77.9036),
        "palacode": (12.2393, 77.938),
        "harur": (12.0504, 78.4798),
        "hoganakkal": (12.1375, 77.7908),
        "krishnagiri": (12.5266, 78.2138),
        "hosur": (12.7409, 77.8253),
        "denkanikottai": (12.549, 77.9971),
        "bargur": (12.4247, 78.3698),
        "pochampalli": (12.3685, 78.213),
        "tirupattur": (12.4968, 78.5723),
        "jolarpet": (12.5697, 78.5813),
        "natrampalli": (12.5499, 78.5929),
        "coimbatore": (11.0168, 76.9558),
        "rs puram": (11.0063, 76.9558),
        "peelamedu": (11.0294, 77.0474),
        "ganapathy": (11.0423, 76.9945),
        "saibaba colony": (11.0233, 77.0127),
        "pappanaickenpalayam": (11.0534, 76.984),
        "singanallur": (10.9987, 77.0467),
        "sulur": (11.0321, 77.1312),
        "thudiyalur": (11.078, 77.0118),
        "kuniyamuthur": (10.9698, 76.9737),
        "saravanampatti": (11.0809, 77.031),
        "kovaipudur": (10.9753, 76.9532),
        "podanur": (10.9834, 76.9889),
        "kavundampalayam": (11.0519, 77.0118),
        "kinathukadavu": (10.8657, 76.9286),
        "pollachi": (10.653, 77.0082),
        "anamalai": (10.591, 77.006),
        "palladam": (10.985, 77.289),
        "tiruppur": (11.1085, 77.3411),
        "avinashi": (11.1945, 77.27),
        "kangayam": (11.0056, 77.5616),
        "dharapuram": (10.7321, 77.5124),
        "udumalaipettai": (10.5839, 77.2482),
        "ooty": (11.4102, 76.695),
        "udhagamandalam": (11.4102, 76.695),
        "coonoor": (11.3531, 76.7941),
        "kotagiri": (11.4249, 76.8643),
        "gudalur": (11.4988, 76.4949),
        "masinagudi": (11.565, 76.6374),
        "erode": (11.341, 77.7172),
        "perundurai": (11.2739, 77.5832),
        "bhavani": (11.4445, 77.6821),
        "gobichettipalayam": (11.4523, 77.4442),
        "sathiyamangalam": (11.5028, 77.2374),
        "anthiyur": (11.5749, 77.5983),
        "nambiyur": (11.3957, 77.2965),
        "karur": (10.9601, 78.0765),
        "aravakurichi": (10.8562, 78.1193),
        "kulithalai": (10.933, 78.4224),
        "manmangalam": (10.892, 78.1834),
        "trichy": (10.7905, 78.7047),
        "tiruchirappalli": (10.7905, 78.7047),
        "srirangam": (10.8617, 78.6904),
        "thillai nagar": (10.8231, 78.7101),
        "k k nagar trichy": (10.8023, 78.6863),
        "ariyamangalam": (10.847, 78.7681),
        "musiri": (10.9444, 78.4511),
        "thuraiyur": (11.1446, 78.5898),
        "perambalur": (11.2314, 78.8803),
        "ariyalur": (11.1427, 79.0782),
        "thanjavur": (10.787, 79.1378),
        "kumbakonam": (10.9602, 79.3845),
        "papanasam": (10.9312, 79.3181),
        "pattukottai": (10.4189, 79.3192),
        "orathanadu": (10.5935, 79.306),
        "budalur": (10.749, 79.0453),
        "thiruvaiyaru": (10.8756, 79.0958),
        "nagapattinam": (10.7672, 79.8449),
        "mayiladuthurai": (11.1016, 79.6518),
        "sirkali": (11.2261, 79.7429),
        "karaikal": (10.9254, 79.838),
        "vedaranyam": (10.3742, 79.8496),
        "tiruvarur": (10.7726, 79.6368),
        "mannargudi": (10.663, 79.4537),
        "needamangalam": (10.8165, 79.4742),
        "pudukkottai": (10.3799, 78.8211),
        "aranthangi": (10.1697, 79.0823),
        "karambakkudi": (10.466, 78.8005),
        "thirumayam": (10.2637, 78.7556),
        "sivaganga": (9.8436, 78.4767),
        "karaikudi": (10.0734, 78.7803),
        "manamadurai": (9.6883, 78.4607),
        "devakottai": (9.9512, 78.8284),
        "madurai": (9.9252, 78.1198),
        "k k nagar": (9.9271, 78.1092),
        "anna nagar madurai": (9.9508, 78.1126),
        "thiruparankundram": (9.887, 78.0816),
        "thirumangalam": (9.8223, 78.0768),
        "usilampatti": (9.9664, 77.772),
        "melur": (10.0352, 78.3344),
        "sholavandan": (9.9967, 78.034),
        "peraiyur": (9.7892, 78.3037),
        "dindigul": (10.3624, 77.9695),
        "palani": (10.4487, 77.5242),
        "natham": (10.194, 77.9824),
        "oddanchatram": (10.3025, 77.7546),
        "vedasandur": (10.5254, 77.9523),
        "batlagundu": (10.1657, 77.7554),
        "theni": (10.0104, 77.4772),
        "periyakulam": (10.1243, 77.5512),
        "bodinayakanur": (10.0054, 77.3559),
        "gudalur theni": (10.0614, 77.5035),
        "uthamapalayam": (9.8076, 77.3244),
        "kumuli": (9.5966, 77.1647),
        "virudhunagar": (9.5847, 77.9637),
        "sivakasi": (9.4533, 77.7989),
        "sattur": (9.3496, 77.9109),
        "rajapalayam": (9.4468, 77.5502),
        "srivilliputhur": (9.509, 77.6357),
        "aruppukkottai": (9.5084, 78.0979),
        "thiruchuli": (9.4939, 78.1258),
        "ramanathapuram": (9.3712, 78.8305),
        "rameswaram": (9.2881, 79.3129),
        "paramakudi": (9.5427, 78.5949),
        "kamuthi": (9.4108, 78.3738),
        "keelakarai": (9.2427, 78.7812),
        "mandapam": (9.274, 79.127),
        "thoothukudi": (8.7642, 78.1348),
        "tuticorin": (8.7642, 78.1348),
        "kovilpatti": (9.1673, 77.8643),
        "tiruchendur": (8.4972, 78.1192),
        "srivaikundam": (8.629, 77.9051),
        "kayalpatnam": (8.5696, 78.1239),
        "tirunelveli": (8.7139, 77.7567),
        "palayamkottai": (8.7115, 77.7352),
        "melapalayam": (8.7014, 77.744),
        "nanguneri": (8.4836, 77.6575),
        "sankarankovil": (9.1664, 77.5516),
        "cheranmahadevi": (8.7432, 77.5867),
        "tenkasi": (8.9601, 77.3152),
        "alangulam": (8.8713, 77.5115),
        "courtallam": (8.9335, 77.2725),
        "nagercoil": (8.1833, 77.4119),
        "kanyakumari": (8.0884, 77.5525),
        "marthandam": (8.3088, 77.235),
        "colachel": (8.1763, 77.2568),
        "padmanabhapuram": (8.25, 77.3333),
        "thuckalay": (8.2396, 77.3003),
        "kulasekharam": (8.4104, 77.1965),
        "uthangarai": (12.32, 78.4267),
        "veppanapalli": (12.46, 78.23),
        "annur": (11.2003, 77.1074),
        "mettupalayam": (11.2977, 76.9388),
        "kallar": (11.3476, 76.8583),
        "coonoor": (11.3531, 76.7941),
    }

    if search_key in KNOWN_LOCATIONS:
        return KNOWN_LOCATIONS[search_key]

    try:
        # Broaden fallback search window to all of Tamil Nadu
        location = geolocator.geocode(f"{area_name}, Tamil Nadu, India")
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None

def filter_hospitals_by_doctor(doctor_type):
    """Filter hospitals that have the required doctor specialty."""
    doctor_type = doctor_type.strip().lower()
    
    # Check if the requested doctor type is in the 'departments' list of the hospital
    def has_department(departments_str):
        if pd.isna(departments_str): return False
        # Strip surrounding quotes if any, then split on semicolons
        clean = str(departments_str).strip('"').strip("'")
        depts = [d.strip().lower() for d in clean.replace(';', ',').split(',')]
        return doctor_type in depts

    filtered = HOSPITALS[HOSPITALS["departments"].apply(has_department)].copy()
    return filtered

def get_realtime_wait(hospital_name, hospital_type, base_wait_min):
    """
    Simulate real-time waiting using time-of-day & day-of-week hospital load patterns.
    
    Algorithm:
    - Base wait = avg_wait_min from CSV (calibrated per hospital type)
    - Multiplied by a TIME LOAD FACTOR derived from hour of day:
        * 8am-11am  = PEAK (morning OPD rush)  -> 1.4x-1.7x
        * 11am-2pm  = HIGH (pre-lunch)         -> 1.2x-1.4x
        * 2pm-5pm   = MEDIUM (afternoon)       -> 0.9x-1.1x
        * 5pm-8pm   = HIGH (evening rush)      -> 1.3x-1.5x
        * 8pm-11pm  = LOW (evening tails)      -> 0.6x-0.8x
        * 11pm-7am  = MINIMAL (night/emergency)-> 0.3x-0.5x
    - Weekend multiplier: Saturday 1.15x, Sunday 0.7x (most OPD closed)
    - Hospital-specific seed: slight variance per hospital name (reproducible within same hour)
    """
    from datetime import datetime
    import math

    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()  # 0=Mon, 6=Sun

    # ── TIME OF DAY MULTIPLIER ──
    if 8 <= hour < 10:
        time_factor = 1.7   # Morning OPD opening rush
    elif 10 <= hour < 12:
        time_factor = 1.5   # Peak morning
    elif 12 <= hour < 14:
        time_factor = 1.2   # Pre-lunch drop
    elif 14 <= hour < 17:
        time_factor = 0.9   # Post-lunch quiet
    elif 17 <= hour < 20:
        time_factor = 1.4   # Evening rush (work-off hours)
    elif 20 <= hour < 23:
        time_factor = 0.7   # Evening wind-down
    else:
        time_factor = 0.35  # Night / emergency only

    # ── WEEKEND ADJUSTMENT ──
    if weekday == 5:   # Saturday
        time_factor *= 1.15
    elif weekday == 6: # Sunday — most OPD departments are closed
        time_factor *= 0.65
        base_wait_min = max(15, base_wait_min)  # Emergency only

    # ── PER-HOSPITAL DETERMINISTIC VARIANCE (same within an hour, changes each hour) ──
    seed = (sum(ord(c) for c in hospital_name) + hour) % 15  # 0-14 mins variance
    
    dynamic_wait = (base_wait_min * time_factor) + seed
    return max(10, round(dynamic_wait))

def predict_wait_and_bed():
    """Predict bed availability using ML model."""
    if rf_clf is None:
        return 1
    sample = pd.DataFrame([{
        "num_lab_procedures": 45,
        "num_procedures": 2,
        "num_medications": 10,
        "time_in_hospital": 5
    }])
    predicted_bed = rf_clf.predict(sample)[0]
    return predicted_bed

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """API endpoint to receive user location and required specialty (or symptom) and recommend the best hospital."""
    if HOSPITALS.empty:
        return jsonify({"error": "Hospital dataset is not loaded on the server."}), 500

    data = request.get_json(silent=True) or {}
    user_location = str(data.get('location', '')).strip()
    doctor_type = str(data.get('specialty', '')).strip()
    symptom_text = str(data.get('symptom', '')).strip()
    
    predicted_by_ai = False
    ai_confidence = 0.0

    # AI Layer: If symptom is typed, use classifier to choose specialty
    if symptom_text and symptom_classifier is not None:
        try:
            prediction = symptom_classifier.predict([symptom_text])[0]
            confidence_array = symptom_classifier.predict_proba([symptom_text])[0]
            import numpy as np
            
            doctor_type = prediction
            ai_confidence = float(np.max(confidence_array))
            predicted_by_ai = True
            print(f"AI Triage: Symptom '{symptom_text}' => {doctor_type} ({ai_confidence*100:.1f}%)")
        except Exception as e:
            print(f"AI Inference error: {e}")
    
    if not user_location or not doctor_type:
        return jsonify({"error": "Missing 'location' or specialist selection."}), 400

    print(f"Received request: Location '{user_location}', Specialty '{doctor_type}'")
    
    # 1. Convert user location string to coordinates
    user_lat, user_lon = geocode_location(user_location)
    if user_lat is None or user_lon is None:
        return jsonify({"error": f"Could not find coordinates for location: {user_location}. Try another area (e.g., 'Adyar', 'Guindy')."}), 404

    # 2. Filter hospitals by doctor type
    eligible = filter_hospitals_by_doctor(doctor_type)
    if eligible.empty:
        return jsonify({"error": "No hospitals found offering this specialty."}), 404

    # 3. Calculate distance using geopy geodesic (more accurate than standard Haversine, but similar)
    user_coords = (user_lat, user_lon)
    eligible["distance_km"] = eligible.apply(
        lambda r: geodesic(user_coords, (r.lat, r.lon)).km, axis=1
    )

    # 4. Predict Bed Availability using ML model
    predicted_bed = predict_wait_and_bed()

    # 5. Compute REAL-TIME wait per hospital (time-of-day aware)
    eligible["predicted_wait"] = eligible.apply(
        lambda r: get_realtime_wait(r["name"], r.get("hospital_type", "multi"), float(r.get("avg_wait_min", 30))),
        axis=1
    )
    eligible["bed_available"] = predicted_bed

    # 6. Ranking: Sort by distance, then dynamic wait
    eligible = eligible.sort_values(by=["distance_km", "predicted_wait"])

    def wait_level(mins):
        if mins <= 20: return "Low"
        if mins <= 45: return "Moderate"
        if mins <= 70: return "High"
        return "Very High"

    # Top recommendation
    best = eligible.iloc[0]

    from datetime import datetime
    now = datetime.now()

    response = {
        "success": True,
        "computed_at": now.strftime("%I:%M %p, %A"),
        "ai_triage": {
            "predicted_by_ai": predicted_by_ai,
            "ai_confidence": round(ai_confidence, 4),
            "symptom_text": symptom_text
        },
        "request": {
            "doctor_type": doctor_type,
            "user_location": user_location,
            "user_coordinates": {"lat": user_lat, "lon": user_lon}
        },
        "recommendation": {
            "name": best["name"],
            "distance_km": round(best["distance_km"], 2),
            "estimated_wait_min": int(best["predicted_wait"]),
            "wait_level": wait_level(best["predicted_wait"]),
            "bed_available": bool(predicted_bed == 1),
            "coordinates": {"lat": best["lat"], "lon": best["lon"]}
        },
        "alternatives": [
            {
                "name": row["name"],
                "distance_km": round(row["distance_km"], 2),
                "estimated_wait_min": int(row["predicted_wait"]),
                "wait_level": wait_level(row["predicted_wait"]),
                "bed_available": bool(predicted_bed == 1)
            } for _, row in eligible.iloc[1:6].iterrows()
        ]
    }

    return jsonify(response)

if __name__ == '__main__':
    print("Starting Flask API server on port 5000...")
    app.run(debug=True, port=5000)
