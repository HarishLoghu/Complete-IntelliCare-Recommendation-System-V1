from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import math
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

app = Flask(__name__)
# Enable CORS for all origins so React can communicate with Flask
CORS(app)

# Load machine learning models and data at startup
try:
    print("Loading models and hospital data...")
    lr_model = joblib.load('linear_regression_wait_time.pkl')
    rf_clf = joblib.load('random_forest_bed_clf.pkl')
    HOSPITALS = pd.read_csv('hospitals_data.csv')
    print("Successfully loaded backend models.")
except FileNotFoundError as e:
    print(f"File not found: {e}. Please run `python train_dummy_models.py` first.")
    exit(1)

# Initialize geolocator
geolocator = Nominatim(user_agent="hospital-recommendation-system")

def geocode_location(area_name):
    """Convert an area name in Chennai to latitude/longitude."""
    try:
        # Focusing on Chennai for the dummy dataset
        location = geolocator.geocode(f"{area_name}, Chennai, Tamil Nadu, India")
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
        depts = [d.strip().lower() for d in str(departments_str).split(',')]
        return doctor_type in depts

    filtered = HOSPITALS[HOSPITALS["departments"].apply(has_department)].copy()
    return filtered

def predict_wait_and_bed():
    """Predict wait time and bed availability for a given hospital."""
    # Using baseline average stats for demonstration purposes
    sample = pd.DataFrame([{
        "num_lab_procedures": 45,
        "num_procedures": 2,
        "num_medications": 10,
        "time_in_hospital": 5
    }])
    
    predicted_wait = lr_model.predict(sample)[0]
    predicted_bed = rf_clf.predict(sample)[0]
    
    return predicted_wait, predicted_bed

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """API endpoint to receive user location and required specialty and recommend the best hospital."""
    data = request.json
    user_location = data.get('location')
    doctor_type = data.get('specialty')
    
    if not user_location or not doctor_type:
        return jsonify({"error": "Missing 'location' or 'specialty' in request payload."}), 400

    print(f"Received request: Location '{user_location}', Specialty '{doctor_type}'")
    
    # 1. Convert user location string to coordinates
    user_lat, user_lon = geocode_location(user_location)
    if not user_lat or not user_lon:
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

    # 4. Predict Waiting Time and Bed Availability for each hospital
    # In a real app, you would pass specific hospital features. We'll add some randomness to the dummy baseline to make hospitals differ.
    import numpy as np
    
    predicted_wait, predicted_bed = predict_wait_and_bed()
    # Adding slight variance per hospital based on distance just for demo variety
    eligible["predicted_wait"] = eligible["distance_km"].apply(lambda d: predicted_wait + d * 0.5 + np.random.normal(0, 5))
    # Bed availability (0 or 1)
    eligible["bed_available"] = predicted_bed 

    # 5. Ranking Logic: Sort by Wait Time primarily, then distance
    eligible = eligible.sort_values(by=["predicted_wait", "distance_km"])
    
    # Top recommendation
    best = eligible.iloc[0]
    
    response = {
        "success": True,
        "request": {
            "doctor_type": doctor_type,
            "user_location": user_location,
            "user_coordinates": {"lat": user_lat, "lon": user_lon}
        },
        "recommendation": {
            "name": best["name"],
            "distance_km": round(best["distance_km"], 2),
            "estimated_wait_min": max(10, round(best["predicted_wait"])), # Ensure wait time isn't negative
            "bed_available": bool(best["bed_available"] == 1),
            "coordinates": {"lat": best["lat"], "lon": best["lon"]}
        },
        # Returning top 3 alternatives as well
        "alternatives": [
            {
                "name": row["name"],
                "distance_km": round(row["distance_km"], 2),
                "estimated_wait_min": max(10, round(row["predicted_wait"])),
                "bed_available": bool(row["bed_available"] == 1)
            } for index, row in eligible.iloc[1:4].iterrows()
        ]
    }
    
    return jsonify(response)

if __name__ == '__main__':
    print("Starting Flask API server on port 5000...")
    app.run(debug=True, port=5000)
