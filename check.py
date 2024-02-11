import requests





import requests

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


print(predict_learning_level(0.5, 'conceptual', 9918))


