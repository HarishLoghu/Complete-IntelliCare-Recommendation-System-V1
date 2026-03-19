import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib
import os

# 1. EXPANDED TRAINING DATASET
# (Typical things a regular user would type)
data = [
    # ── Cardiologist ──
    ("sudden sharp chest pain with left arm numbness", "Cardiologist"),
    ("difficulty breathing, heart is racing fast, palpitations", "Cardiologist"),
    ("heavy pressure in the chest and dizziness", "Cardiologist"),
    ("shortness of breath during minor walking and cold sweats", "Cardiologist"),
    ("high blood pressure and irregular heartbeat rhythm", "Cardiologist"),
    
    # ── Neurologist ──
    ("unbearable headache, visual layout is blurred", "Neurologist"),
    ("sudden numbness on right side of face, slurred speech", "Neurologist"),
    ("frequent seizures and losing consciousness for short intervals", "Neurologist"),
    ("constant dizziness, loss of balance, and memory fog", "Neurologist"),
    ("tremors in hands and chronic insomnia with migraines", "Neurologist"),

    # ── Orthopedician ──
    ("fractured my wrist in a motorcycle accident, severe swelling", "Orthopedician"),
    ("constant lower back pain shooting down into my leg", "Orthopedician"),
    ("twisted my ankle while running, cannot place any weight", "Orthopedician"),
    ("knee joint is clicking and locking when I bend it", "Orthopedician"),
    ("severe arthritis pain in fingers stiffness every morning", "Orthopedician"),

    # ── Dermatologist ──
    ("red itchy rash spread across my neck and chest", "Dermatologist"),
    ("severe acne breakout that is leaving scars", "Dermatologist"),
    ("scaly dry skin patches patches on elbows", "Dermatologist"),
    ("fungal infection on feet not going away with cream", "Dermatologist"),
    ("hair loss and dandruff with constant scalp irritation", "Dermatologist"),

    # ── Gynecologist ──
    ("severe menstrual cramps and irregular heavy bleeding", "Gynecologist"),
    ("doing regular check up for 3-months pregnancy", "Gynecologist"),
    ("pain in the lower pelvic area and nausea in morning", "Gynecologist"),
    ("abnormal vaginal discharge and burning sensation", "Gynecologist"),
    ("menopause symptoms like hot flashes and mood swings", "Gynecologist"),

    # ── Pediatrician ──
    ("my 3 year old child has intense fever and cough", "Pediatrician"),
    ("baby has been crying constantly with stomach pain", "Pediatrician"),
    ("need routine vaccination drops for 6 month old infant", "Pediatrician"),
    ("toddler has loss of appetite and vomiting repeatedly", "Pediatrician"),
    ("kid has a high temperature and runny nose for 2 days", "Pediatrician"),

    # ── Oncologist ──
    ("found a hard painless lump in my breast region", "Oncologist"),
    ("unexplained weight loss of 10kg and chronic fatigue", "Oncologist"),
    ("biopsy test results suggest abnormal cell growth", "Oncologist"),
    ("need to schedule next chemotherapy or radiation seating", "Oncologist"),
    ("persistent dry cough for months with blood traces", "Oncologist"),

    # ── General Physician (Fall back for common ailments) ──
    ("general viral fever with body ache and sore throat", "General Physician"),
    ("stomach flu, continuous loose motion, and dehydration", "General Physician"),
    ("dry cough and sneezing due to seasonal allergies", "General Physician"),
    ("mild food poisoning with acidity and vomiting", "General Physician"),
    ("feeling weak and tired, need blood pressure checkup", "General Physician"),
]

print("Preprocessing dataset with %d entries..." % len(data))

df = pd.DataFrame(data, columns=["text", "specialty"])

# 2. CREATE NLP PIPELINE
# TF-IDF converts text into math vectors; LogisticRegression classifies them.
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        max_features=1000, 
        ngram_range=(1, 2), # factor in phrases like 'chest pain'
        stop_words='english'
    )),
    ('clf', LogisticRegression(C=10.0, max_iter=200))
])

# 3. TRAIN THE MODEL
print("Training AI classification model...")
pipeline.fit(df["text"], df["specialty"])

# Test prediction
test_text = "i am dizzy and my left arm is going numb with chest tightness"
predicted = pipeline.predict([test_text])[0]
prob = np.max(pipeline.predict_proba([test_text]))

print("\n--- AI TEST PREDICTION ---")
print("Input: ", test_text)
print("Predicted: %s (%.2f%% confidence)" % (predicted, prob * 100))

# 4. SAVE WEIGHTS
joblib.dump(pipeline, 'symptom_classifier.pkl')
print("\nSaved model to symptom_classifier.pkl successfully!")
