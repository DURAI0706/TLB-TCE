import sys
import os
from flask import Flask
from pymongo import MongoClient
import sys
import os
import pandas as pd
import numpy as np
import joblib
import requests
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

app = Flask(__name__)
app.secret_key = 'sawq#@21'
connection_string = "mongodb+srv://hackers:hackers123@psg.kmis61j.mongodb.net/"
client = MongoClient(connection_string)
db = client['python']

def train_model():
    students_collection = db['students']
    cursor = students_collection.find().limit(300)
    data = list(cursor)
    df = pd.DataFrame(data)
    types_mapping = {'conceptual': 0, 'application': 1, 'problem solving': 2}
    df['highest_incorrect_type'] = df['highest_incorrect_type'].map(types_mapping)

    # Fill NaN values with a default value if needed
    df['highest_incorrect_type'].fillna(-1, inplace=True)

    df['time_taken'] = df['time_taken'].astype(float)
    df['correct_ratio'] = df['correct_ratio'].astype(float)
    level_mapping = {'quick learner': 0, 'average learner': 1, 'slow learner': 2}
    df['learning_level'] = df['learning_level'].map(level_mapping)
    df['learning_level'].fillna(-1, inplace=True)
    df['learning_level'] = pd.to_numeric(df['learning_level'], errors='coerce', downcast='integer')

    # Drop rows with non-finite values
    df = df.dropna(subset=['learning_level'])

    le = LabelEncoder()
    df['learning_level'] = le.fit_transform(df['learning_level'])

    # Encode 'learning_level' column
    level_mapping = {'quick learner': 0, 'average learner': 1, 'slow learner': 2}
    features = ['time_taken', 'correct_ratio', 'highest_incorrect_type']
    target = 'learning_level'

    X = df[features]
    y = df[target]

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Create a Random Forest Classifier
    clf = RandomForestClassifier(n_estimators=100, random_state=42)

    # Fit the model
    clf.fit(X_train, y_train)

    # Make predictions on the test set
    y_pred = clf.predict(X_test)

    # Evaluate the model
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)

    print(f"Accuracy: {accuracy}")
    print("Classification Report:\n", report)

    joblib.dump(clf, 'random_forest_model.joblib')
    joblib.dump(le, 'label_encoder.joblib')




def predict_learning_level(correct_ratio, highest_incorrect_type, time_taken):
    model_server_url = "http://localhost:8000/predict/"
    request_data = {
        "correct_ratio": correct_ratio,
        "highest_incorrect_type": highest_incorrect_type,
        "time_taken": time_taken
    }

    # Make a POST request to the model server
    response = requests.post(model_server_url, json=request_data)

    # Return the prediction received from the model server
    return response.json()['predicted_learning_level']



if __name__ == "__main__":
    # Extract command line arguments
    correct_ratio = float(sys.argv[1])
    highest_incorrect_type = sys.argv[2]
    time_taken = float(sys.argv[3])
    # Predict learning levels
    prediction = predict_learning_level(correct_ratio, highest_incorrect_type, time_taken)
    print(prediction)
