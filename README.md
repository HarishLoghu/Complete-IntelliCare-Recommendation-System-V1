# Intelligent Hospital Recommendation System

This project contains the complete web application for your hospital recommendation system.

## Project Structure
- `backend/`: Contains the Flask API, the machine learning models (generated dynamically), and geocoding logic.
- `frontend/`: Contains the React/Vite user interface.

## Prerequisites
- Python 3.9+ installed
- Node.js installed

## How to Run the Project (Step-by-Step)

### 1. Start the Backend API (Flask)
1. Open a terminal and navigate to the `backend` folder:
   ```cmd
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```cmd
   python -m venv venv
   call venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Generate the Machine Learning models (this replaces your Colab run for now):
   ```cmd
   python train_dummy_models.py
   ```
4. Start the server:
   ```cmd
   python app.py
   ```
   *The backend will now be running on http://127.0.0.1:5000*

### 2. Start the Frontend (React)
1. Open a **second** terminal and navigate to the `frontend` folder:
   ```cmd
   cd frontend
   ```
2. Install dependencies (if you haven't already):
   ```cmd
   npm install
   ```
3. Start the Vite development server:
   ```cmd
   npm run dev
   ```
4. Open the link provided in the terminal (usually http://localhost:5173) in your browser.

## Using Your Real ML Models
When you are ready to use your real data:
1. Save `linear_regression_wait_time.pkl` and `random_forest_bed_clf.pkl` from your Colab notebook.
2. Replace the `.pkl` files and `hospitals_data.csv` inside the `backend` folder with your real ones.
3. Restart the Flask app.
