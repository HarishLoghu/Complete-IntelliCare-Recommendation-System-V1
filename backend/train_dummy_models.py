import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import random
import os

print("Generating dummy models and data for local testing...")

# 1. Generate Hospitals Data
print("Generating dummy hospitals dataset...")
SPECIALTIES = [
    "Cardiologist",
    "Orthopedician",
    "Neurologist",
    "General Physician",
    "Pediatrician",
    "Gynecologist"
]

hospitals = [
    {"name": "Apollo Hospitals, Greams Road", "lat": 13.0610, "lon": 80.2520},
    {"name": "Fortis Malar Hospital, Adyar", "lat": 13.0076, "lon": 80.2558},
    {"name": "Miot International, Manapakkam", "lat": 13.0189, "lon": 80.1804},
    {"name": "Global Health City, Perumbakkam", "lat": 12.8988, "lon": 80.2016},
    {"name": "Kauvery Hospital, Alwarpet", "lat": 13.0336, "lon": 80.2530},
    {"name": "Billroth Hospitals, Aminjikarai", "lat": 13.0734, "lon": 80.2223},
    {"name": "Vijaya Hospital, Vadapalani", "lat": 13.0489, "lon": 80.2104},
    {"name": "Rajiv Gandhi Government General Hospital", "lat": 13.0818, "lon": 80.2764},
    {"name": "SRM Institutes for Medical Science, Vadapalani", "lat": 13.0514, "lon": 80.2120},
    {"name": "Sri Ramachandra Medical Centre", "lat": 13.0396, "lon": 80.1465}
]

HOSPITALS = pd.DataFrame(hospitals)
np.random.seed(42)
random.seed(42)

HOSPITALS["departments"] = HOSPITALS["name"].apply(
    lambda x: ",".join(random.sample(SPECIALTIES, k=random.randint(2, 4)))
)
# Save generated dummy hospitals dataset
HOSPITALS.to_csv("hospitals_data.csv", index=False)
print("Saved hospitals_data.csv")

# 2. Generate Dummy Data for Wait Time Regression
print("Training dummy Wait Time Model (Linear Regression)...")
df_wait = pd.DataFrame({
    'num_lab_procedures': np.random.randint(10, 80, 500),
    'num_procedures': np.random.randint(0, 5, 500),
    'num_medications': np.random.randint(1, 40, 500),
    'time_in_hospital': np.random.randint(1, 14, 500)
})
# Synthetic wait time logic
df_wait['waiting_time'] = (
    df_wait['num_lab_procedures'] * 0.5 + 
    df_wait['num_procedures'] * 5 + 
    df_wait['num_medications'] * 0.2 + 
    np.random.normal(0, 5, 500)
)
X_wait = df_wait[['num_lab_procedures', 'num_procedures', 'num_medications', 'time_in_hospital']]
y_wait = df_wait['waiting_time']
lr = LinearRegression()
lr.fit(X_wait, y_wait)
joblib.dump(lr, "linear_regression_wait_time.pkl")
print("Saved linear_regression_wait_time.pkl")

# 3. Generate Dummy Data for Bed Availability Classification
print("Training dummy Bed Availability Model (Random Forest Classifier)...")
y_bed = np.where(df_wait['time_in_hospital'] + np.random.normal(0, 2, 500) < 8, 1, 0) # 1 = yes, 0 = no
rf_clf = RandomForestClassifier(n_estimators=50, random_state=42)
rf_clf.fit(X_wait, y_bed)
joblib.dump(rf_clf, "random_forest_bed_clf.pkl")
print("Saved random_forest_bed_clf.pkl")

print("\nSuccess! All models and data required to run the backend are generated.")
