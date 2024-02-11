from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd
import os

app = FastAPI()

class LearningLevelPredictionRequest(BaseModel):
    correct_ratio: float
    highest_incorrect_type: str
    time_taken: float

class LearningLevelPredictionResponse(BaseModel):
    predicted_learning_level: str

# Load the model and label encoder when the FastAPI app starts
model_filename = 'random_forest_model.joblib'
label_encoder_filename = 'label_encoder.joblib'

clf = joblib.load(model_filename)
le = joblib.load(label_encoder_filename)

def predict_learning_level(correct_ratio, highest_incorrect_type, time_taken):
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

@app.post("/predict/")
def predict(request_data: LearningLevelPredictionRequest) -> LearningLevelPredictionResponse:
    predicted_learning_level = predict_learning_level(request_data.correct_ratio, request_data.highest_incorrect_type, request_data.time_taken)
    return LearningLevelPredictionResponse(predicted_learning_level=predicted_learning_level)

