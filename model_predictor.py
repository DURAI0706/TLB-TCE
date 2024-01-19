import sys
import os
from flask import Flask
from pymongo import MongoClient
import sys
import os
import pandas as pd
import numpy as np
from sklearn.externals import joblib
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
    model_filename = 'random_forest_model.joblib'
    label_encoder_filename = 'label_encoder.joblib'

    # Check if the model file and label encoder file exist
    if not os.path.isfile(model_filename) or not os.path.isfile(label_encoder_filename):
        print(f"Model file {model_filename} or label encoder file {label_encoder_filename} not found. Training the model...")
        train_model()

    # Load the trained model and label encoder
    clf = joblib.load(model_filename)
    le = joblib.load(label_encoder_filename)

    # Create a DataFrame with the new data
    new_data = pd.DataFrame({
        'time_taken': [time_taken],
        'correct_ratio': [correct_ratio],
        'highest_incorrect_type': [highest_incorrect_type]
    })

    # Load label encoding mappings
    types_mapping = {'conceptual': 0, 'application': 1, 'problem solving': 2}
    # Map 'highest_incorrect_type' to numerical values using the same mapping as before
    new_data['highest_incorrect_type'] = new_data['highest_incorrect_type'].map(types_mapping)

    # Convert 'Time_taken' to float
    new_data['time_taken'] = new_data['time_taken'].astype(float)

    # Make predictions on new data
    predicted_learning_level_encoded = clf.predict(new_data)[0]

    # Decode the predicted label to get the learning level
    predicted_learning_level = le.inverse_transform([predicted_learning_level_encoded])[0]

    if predicted_learning_level == 0:
        return 'quick learner'
    elif predicted_learning_level == 1:
        return 'average learner'
    elif predicted_learning_level == 2:
        return 'slow learner'

if __name__ == "__main__":
    # Extract command line arguments
    correct_ratio = float(sys.argv[1])
    highest_incorrect_type = sys.argv[2]
    time_taken = float(sys.argv[3])
    # Predict learning levels
    prediction = predict_learning_level(correct_ratio, highest_incorrect_type, time_taken)
    print(prediction)
