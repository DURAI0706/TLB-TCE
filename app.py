from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, flash, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from transformers import PreTrainedTokenizerFast, TFBertForSequenceClassification
import os
import bcrypt  
import joblib
from transformers import AutoTokenizer, TFAutoModel
from flask import jsonify
from tensorflow.keras.layers import Embedding, LSTM, Dense, Input
from tensorflow.keras.models import Model
from flask import render_template, redirect, session, send_from_directory
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from collections import Counter
from tensorflow.keras.models import Sequential, load_model
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta, timezone
import time
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OrdinalEncoder
import skfuzzy as fuzz
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from keras.utils import to_categorical
import matplotlib.pyplot as plt 
from datetime import timedelta
import subprocess  
from jinja2 import Environment

app = Flask(__name__)
app.secret_key = "sawq#@21"

connection_string = f"mongodb+srv://hackers:hackers123@psg.kmis61j.mongodb.net/"
client = MongoClient(connection_string)
db = client['gamification']
student_collection = db['student']
recommendation_collection = db['recommendation'] 
teacher_collection= db['teacher']
courses_collection=db['courses']
mycourses_collection=db['mycourses']
quiz_collection=db['quiz']
assignment_collection=db['assignment']
student_test_collection= db['quizsubmission']
material_collection= db['material_collection']
slow_collection = db['slow_learners']
students_collection = db['students']
new_collection=db['new_users']
mannur_collection=db['mannur']
students_assignment=db['student_assignment']
learning_collection=db['learning_level']
leaderboard_collection=db['leaderboard']
collection = db["student_assignment"]


def get_unique_options():
    unique_courses = collection.distinct("course_name")
    unique_quiz_names = collection.distinct("quiz_name")
    unique_assignments = collection.distinct("assignment")

    return unique_courses, unique_quiz_names, unique_assignments

# Define a custom filter function to emulate enumerate
def utility_processor():
    def custom_enumerate(iterable, start=0):
        return enumerate(iterable, start)

    return dict(enumerate=custom_enumerate)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/role', methods=['GET', 'POST'])
def role():
    if request.method == 'POST':
        selected_role = request.form['role']
        session['selected_role'] = selected_role
        if selected_role == 'student':
            return redirect('/studentlogin')  
        elif selected_role == 'teacher':
            return redirect('/teacherlogin')
    return render_template('role.html')


#----------------------------------------<student>------------------------------------------------------------------------------------
@app.route('/studentregister', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        name = request.form.get('name')
        register_number = request.form.get('register_number')
        roll_number = request.form.get('roll_number')
        department = request.form.get('department')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not email.endswith('student.tce.edu'):
            flash('Invalid email format')
            return redirect('/studentregister')
        existing_user = student_collection.find_one({'email': email})
        if existing_user:
            flash('Email already exists')
            return redirect('/studentregister')
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect('/studentregister')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {
            'name': name,
            'register_number': register_number,
            'roll_number': roll_number,
            'department': department,
            'email': email,
            'password': hashed_password,
            'learning_level':'average learner',
            'role': 'student',
            'total_coins':500,
            'total_keys' :1,
            'total_heart' :2
        }
        result = student_collection.insert_one(user_data)
        new_d=new_collection.insert_one(user_data)
        zigo= mannur_collection.insert_one(user_data)
        nico= learning_collection.insert_one(user_data)
        if result.inserted_id:
            session['email'] = email
        return redirect('/recommendation')
    return render_template('studentregister.html')

@app.route('/studentlogin', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        student = student_collection.find_one({'email': email, 'role': 'student'})
        if student and bcrypt.checkpw(password.encode('utf-8'), student['password']):
            session['user_id'] = str(student['_id'])
            student_data = student_collection.find_one({'email': email})
            if student_data:
                print("Total Coins:", student_data.get('total_coins', 'Not Found'))
                template_context = {
                    'name': student_data['name'],
                    'role': student_data['role'],
                    'email': student_data['email'],
                    'department': student_data['department'],
                    'roll_number': student_data['roll_number'],
                    'register_number': student_data['register_number'],
                    'total_coins': student_data.get('total_coins', 0),
                    'total_keys': student_data.get('total_keys', 0),
                    'total_heart': student_data.get('total_heart', 0)
                }
                session['student_email'] = email
                recommendation_data = recommendation_collection.find_one({'user_id': email})
                recommendation_result = recommendation_data.get('recommendation') if recommendation_data else None
                if recommendation_result:
                    print(f'Recommendation for {email}: {recommendation_result}')
                    if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                        return render_template('horror_dashboard.html', student_data=template_context)
                    elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                        return render_template('natural_dashboard.html', student_data=template_context)
                    else:
                        return render_template('fantasy_dashboard.html', student_data=template_context)
            return redirect('/studentlogin')
    return render_template('studentlogin.html')

def map_fn(raw_values):
    column_mapping = {
        'Gender': 'Gender',
        'I typically play videogames /online games': 'a',
        'I prefer the following way of playing video/online games:': 'b',
        'Exploring hidden treasures': 'c',
        "Finding what's behind a locked door": 'd',
        'Giving Hint to others': 'e',
        'Picking up every single collectible in an area': 'f',
        'Thirst to crack more challenges': 'g',
        'Improve myself by self competing': 'h',
        'Playing in a group': 'i',
        'Cooperating with strangers': 'j',
        'Share your success with others': 'k',
        'Taking on a strong opponent when playing one to one match': 'l',
        'Getting 100% (completing everything in a game)': 'm',
        'Giving more importance to achieving goals': 'n',
        'I understand something better after I': 'o',
        'When I have to work on a group project, I first want to': 'p',
        'I more easily remember': 'q',
        'When I am doing long calculations,': 'r',
        'When I am reading for enjoyment, I like writers to': 's',
        'When I have to perform a task, I prefer to': 't',
        'When someone is showing me data, I prefer': 'u',
        'When I am learning a new subject, I prefer to': 'v',
        'When considering a body of information, I am more likely to': 'w',
        'When I solve math problems': 'x',
        'My attitude to videogame stories is:': 'y',
        'Do you like to do time-bound challenges?': 'z',
        'Choose a theme you like the most': 'aa',
        'Which design of points you like the most?': 'bb',
        'If you cross an important milestone in a game, Which design of Badges you like the most?': 'cc',
        'If you want a leaderboard for your game scores, which of the designs you like the most?': 'dd',
        'When you want to monitor your progress in a game and unlock the next level, Which design of levels you like the most?': 'ee',
        'Which Appreciation Animation that you would like to have when you complete a task?': 'ff',
        'Do you love it, if you see these many game elements into your learning Management system?': 'gg'
    }
    preferences_mappings = {
        'Gender': {'Male': 1, 'Female': 2},
        'a': {'Every day': 1, 'Every week': 2, 'Occasionally': 3, 'Rarely': 4, 'Never': 5},
        'b': {'Single Player Alone': 1, 'Single Player with Other Player Helping': 2, 'Multiplayer': 3},
        'c': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'd': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'e': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'f': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'g': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'h': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'i': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'j': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'k': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'l': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'm': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'n': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'o': {'Try It Out': 1, 'Think It Through': 2},
        'p': {"Have 'group brainstorming' where everyone contributes ideas.": 1, 'Brainstorm individually and then come together as a group to compare ideas': 2},
        'q': {'Something I have done.': 1, 'Something I have thought a lot about': 2},
        'r': {'I tend to repeat all my steps and check my work carefully.': 1, 'I find checking my work tiresome and have to force myself to do it': 2},
        's': {'Clearly say what they mean.': 1, 'Say things in creative, interesting ways': 2},
        't': {'Master one way of doing it.': 1, 'Come up with new ways of doing it': 2},
        'u': {'Charts or graphs.': 1, 'Text summarizing the results': 2},
        'v': {'Stay focused on that subject, learning as much about it as I can.': 1, 'Try to make connections between that subject and related subjects': 2},
        'w': {'Focus on details and miss the big picture.': 1, 'Try to understand the big picture before getting into the details': 2},
        'x': {'I usually work my way to the solutions one step at a time.': 1, 'I often just see the solutions but then have to struggle to figure out the steps to get to them': 2},
        'y': {'Stories help me enjoy a videogame.': 1, 'Stories are not important to me in videogames': 2, 'I prefer videogames without stories': 3},
        'z': {'Yes': 1, 'No': 0},
        'aa': {'Alien': 1, 'Living location': 2, 'Nature connected': 3, 'Life style': 4, 'Fantasy': 5, 'Horror': 6},
        'bb': {'1': 1, '2': 2, '3': 3, '4': 4},
        'cc': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, 'I do not wish for any badges': 0},
        'dd': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, 'I do not need a leaderboard': 0},
        'ee': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, 'I do not want any special indication for levels': 0},
        'ff': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6},
        'gg': {'Yes': 1, 'No': 2},
    }
    mapped_values = {}
    for column, value in raw_values.items():
        if column in column_mapping:
            mapped_values[column_mapping[column]] = value
    for column, value in mapped_values.items():
        if column in preferences_mappings:
            mapped_values[column] = preferences_mappings[column].get(value, 0)  
    return mapped_values

@app.route('/recommendation', methods=['GET', 'POST'])
def recommendation():
    if 'email' in session:
        email = session['email']
        personal_details = student_collection.find_one({'email': email})
        if personal_details:
            if request.method == 'POST':
                user_preferences = {
                    'Gender': request.form.get('Gender'),
                    'a': request.form.get('PlayFrequency'),
                    'b': request.form.get('PlayPreference'),
                    'c': request.form.get('ExploringHiddenTreasures'),
                    'd': request.form.get('FindingBehindLockedDoor'),
                    'e': request.form.get('GivingHintToOthers'),
                    'f': request.form.get('PickingUpCollectibles'),
                    'g': request.form.get('ThirstToCrackChallenges'),
                    'h': request.form.get('ImproveMyselfSelfCompeting'),
                    'i': request.form.get('PlayingInAGroup'),
                    'j': request.form.get('CooperatingWithStrangers'),
                    'k': request.form.get('ShareYourSuccess'),
                    'l': request.form.get('TakingOnStrongOpponent'),
                    'm': request.form.get('Getting100'),
                    'n': request.form.get('Givingimportance'),
                    'o': request.form.get('UnderstandBetter'),
                    'p': request.form.get('GroupProject'),
                    'q': request.form.get('EasilyRemember'),
                    'r': request.form.get('LongCalculations'),
                    's': request.form.get('ReadingPreference'),
                    't': request.form.get('TaskPerformance'),
                    'u': request.form.get('DataPresentation'),
                    'v': request.form.get('LearningPreference'),
                    'w': request.form.get('InformationConsideration'),
                    'x': request.form.get('MathProblemSolving'),
                    'y': request.form.get('VideogameStories'),
                    'z': request.form.get('TimeBoundChallenges'),
                    'aa': request.form.get('FavoriteTheme'),
                    'bb': request.form.get('PointsDesign'),
                    'cc': request.form.get('BadgeDesign'),
                    'dd': request.form.get('LeaderboardDesign'),
                    'ee': request.form.get('LevelDesign'),
                    'ff': request.form.get('AppreciationAnimation'),
                    'gg': request.form.get('GameElementsInLMS'),
                }                
                cursor = recommendation_collection.find(
                    {"Your suggestion for designing an immersive gaming experience": {"$ne": "No idea"}},
                    {"_id": 0, "Your suggestion for designing an immersive gaming experience": 0}
                ).limit(208)
                entries_from_database = list(cursor)   
                mapped_entries = [map_fn(entry) for entry in entries_from_database]
                recommendation_result = perform_recommendation(user_preferences, mapped_entries)
                save_recommendation_to_db(email, user_preferences, recommendation_result)
                return redirect(url_for('show_recommendation', recommendation_result=recommendation_result))
                session['recommendation_result'] = recommendation_result
            return render_template('recommendation.html', personal_details=personal_details)
    return redirect('/login')

def perform_recommendation(user_preferences, mapped_entries):
    df_user = pd.DataFrame([user_preferences])
    preferences_mappings = {
        'Gender': {'Male': 1, 'Female': 2},
        'a': {'Every day': 1, 'Every week': 2, 'Occasionally': 3, 'Rarely': 4, 'Never': 5},
        'b': {'Single Player Alone': 1, 'Single Player with Other Player Helping': 2, 'Multiplayer': 3},
        'c': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'd': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'e': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'f': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'g': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'h': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'i': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'j': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'k': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'l': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'm': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'n': {'Love It': 1, 'Like It': 2, 'Dislike It': 3, 'Hate It': 4},
        'o': {'Try It Out': 1, 'Think It Through': 2},
        'p': {"Have 'group brainstorming' where everyone contributes ideas.": 1, 'Brainstorm individually and then come together as a group to compare ideas': 2},
        'q': {'Something I have done.': 1, 'Something I have thought a lot about': 2},
        'r': {'I tend to repeat all my steps and check my work carefully.': 1, 'I find checking my work tiresome and have to force myself to do it.': 2},
        's': {'Clearly say what they mean.': 1, 'Say things in creative, interesting ways.': 2},
        't': {'Master one way of doing it.': 1, 'Come up with new ways of doing it.': 2},
        'u': {'Charts or graphs.': 1, 'Text summarizing the results.': 2},
        'v': {'Stay focused on that subject, learning as much about it as I can.': 1, 'Try to make connections between that subject and related subjects.': 2},
        'w': {'Focus on details and miss the big picture.': 1, 'Try to understand the big picture before getting into the details.': 2},
        'x': {'I usually work my way to the solutions one step at a time.': 1, 'I often just see the solutions but then have to struggle to figure out the steps to get to them.': 2},
        'y': {'Stories help me enjoy a videogame.': 1, 'Stories are not important to me in videogames.': 2, 'I prefer videogames without stories.': 3},
        'z': {'Yes': 1, 'No': 0},
        'aa': {'Alien': 1, 'Living location': 2, 'Nature connected': 3, 'Life style': 4, 'Fantasy': 5, 'Horror': 6},
        'bb': {'1': 1, '2': 2, '3': 3, '4': 4},
        'cc': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, 'I do not wish for any badges': 0},
        'dd': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, 'I do not need a leaderboard': 0},
        'ee': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, 'I do not want any special indication for levels': 0},
        'ff': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6},
        'gg': {'Yes': 1, 'No':2},        
    }
    for column, mapping in preferences_mappings.items():
        df_user[column] = df_user[column].map(mapping)        
    user_aa_value = user_preferences.get('aa', 0) 
    print("user_aa_label:",user_aa_value)
    aa_label = None
    if user_aa_value == 'Nature connected':
        aa_label = 3
    elif  user_aa_value== "Fantasy":
        aa_label = 5
    else:
        aa_label = 1
    df_entries = pd.DataFrame(mapped_entries)
    df_combined = pd.concat([df_user, df_entries], ignore_index=True)
    df_combined.fillna(0, inplace=True)
    input_columns = df_combined.columns[1:]  
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_combined[input_columns])
    try:
        n_clusters = 4
        cntr, u, u0, d, jm, p, fpc = fuzz.cluster.cmeans(X_scaled.transpose(), c=n_clusters, m=4, error=0.005, maxiter=1000, init=None)
        user_cluster = np.argmax(u, axis=0)[0]
        if aa_label == 1:
            recommendation = "based on above we recommend you horror theme to nourish and to grow"
        elif aa_label == 3:
            recommendation = "based on above we recommend you nature content theme to nourish and to grow"  
        else:
            recommendation = "based on above we recommend you fantasy theme to nourish and to grow"
        print(recommendation)
        return recommendation
    except Exception as e:
        print(f"Error during clustering: {e}")
        return "Unable to provide a recommendation at the moment. Please check your preferences and try again."
def save_recommendation_to_db(email, user_preferences, recommendation):
    recommendation_data = {
        'user_id': email,
        'user_preferences': user_preferences,
        'recommendation': recommendation,
           }
    recommendation_collection.insert_one(recommendation_data)

@app.route('/show_recommendation')
def show_recommendation():
    recommendation_result = request.args.get('recommendation_result')
    session.pop('recommendation_result', None)
    return render_template('recommendation_result.html', recommendation_result=recommendation_result)

@app.route("/horror_dashboard")
def horror_dashboard():
    if "email" in session:
        student_data = student_collection.find_one({"email": session["email"]})
        if student_data:
            print("Student Data:", student_data)
            print("Total Coins:", student_data.get("total_coins", "Not Found"))
            template_context = {
                "name": student_data["name"],
                "role": student_data["role"],
                "email": student_data["email"],
                "department": student_data["department"],
                "roll_number": student_data["roll_number"],
                "register_number": student_data["register_number"],
                "total_coins": student_data.get("total_coins", 0),
                "total_keys": student_data.get("total_keys", 0),
                "total_heart": student_data.get("total_heart", 0),
            }
            return render_template("horror_dashboard.html", student_data=template_context)
    return redirect(url_for("studentlogin"))

@app.route("/natural_dashboard")
def natural_dashboard():
    if "email" in session:
        student_data = student_collection.find_one({"email": session["email"]})
        if student_data:
            template_context = {
                "name": student_data["name"],
                "role": student_data["role"],
                "email": student_data["email"],
                "department": student_data["department"],
                "roll_number": student_data["roll_number"],
                "register_number": student_data["register_number"],
                "total_coins": student_data.get("total_coins", 0),
                "total_keys": student_data.get("total_keys", 0),
                "total_heart": student_data.get("total_heart", 0),
            }
            return render_template("natural_dashboard.html", student_data=template_context)
    return redirect(url_for("studentlogin"))

@app.route("/fantasy_dashboard")
def fantasy_dashboard():
    if "email" in session:
        student_data = student_collection.find_one({"email": session["email"]})
        if student_data:
            print("Total Coins:", student_data.get("total_coins", "Not Found"))
            template_context = {
                "name": student_data["name"],
                "role": student_data["role"],
                "email": student_data["email"],
                "department": student_data["department"],
                "roll_number": student_data["roll_number"],
                "register_number": student_data["register_number"],
                "total_coins": student_data.get("total_coins", 0),
                "total_keys": student_data.get("total_keys", 0),
                "total_heart": student_data.get("total_heart", 0),
            }
            return render_template("fantasy_dashboard.html", student_data=template_context)
    return redirect(url_for("studentlogin"))

@app.route('/studentprofile', methods=['GET', 'POST'])
def user_profile():
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
    elif 'email' in session:
        email = session['email']
        student_email = None
    elif 'student_email' in session:
        email = None
        student_email = session['student_email']
        student_details = student_collection.find_one({'email': email or student_email})

    student_data = student_collection.find_one({'email': email or student_email})
    if student_data:
        print("Total Coins:", student_data.get('total_coins', 'Not Found'))
        recommendation_data = recommendation_collection.find_one({'user_id': email or student_email})
        if recommendation_data:
            recommendation_result = recommendation_data.get('recommendation')
        else:
            recommendation_result = None
        template_context = {
            'name': student_data['name'],
            'role': student_data['role'],
            'email': student_data['email'],
            'department': student_data['department'],
            'roll_number': student_data['roll_number'],
            'register_number': student_data['register_number'],
            'total_coins': student_data.get('total_coins', 0),
            'total_keys': student_data.get('total_keys', 0),
            'total_heart': student_data.get('total_heart', 0),
            'recommendation_result': recommendation_result  
        }
        recommendation_result = recommendation_data.get('recommendation') if recommendation_data else None

        if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
            return render_template('horror_dashboard.html', student_data=template_context)
        elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
            return render_template('natural_dashboard.html', student_data=template_context)
        else:
            try:
                return render_template('fantasy_dashboard.html', student_data=template_context)
            except jinja2.exceptions.TemplateNotFound:
                return render_template('default_template.html', student_data=template_context)

@app.route('/mycourses/student', methods=['GET', 'POST'])
def student_courses():
    user_email = session.get('email') or session.get('student_email')
    student_details = student_collection.find_one({'email': user_email})  
    if not student_details:
        return redirect('/role')
    department = student_details.get('department')
    all_courses = list(courses_collection.find())
    joined_courses = mycourses_collection.find({'user_email': user_email})  
    joined_course_names = [joined_course['course_name'] for joined_course in joined_courses]
    my_courses = [course for course in all_courses if course['name'] in joined_course_names and course['department'] == department]
    other_courses = [course for course in all_courses if course['name'] not in joined_course_names and course['department'] == department]
    recommendation_data = recommendation_collection.find_one({'user_id': user_email}) 
    recommendation_result = recommendation_data.get('recommendation') if recommendation_data else None
    if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
        return render_template('mycoursehorror.html', my_courses=my_courses, other_courses=other_courses)
    elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
        return render_template('mycoursenatural.html', my_courses=my_courses, other_courses=other_courses)
    else:
        try:
            return render_template('mycoursefantasy.html', my_courses=my_courses, other_courses=other_courses)
        except jinja2.exceptions.TemplateNotFound:
            return render_template('default_template.html', student_data = template_context)
    
@app.route('/verify_join', methods=['POST'])
def verify_join():
    entered_password = request.form.get('enteredPassword')
    course_name = request.form.get('courseName')
    user_email = session.get('email') or session.get('student_email')
    print("Session Variables in verify_join:", session)
    print("Form Variables - Password:", entered_password)
    print("Form Variables - Course Name:", course_name)
    print("Form Variables - User Email:", user_email)
    if entered_password and course_name and user_email:
        print("Inside if condition")
        course = courses_collection.find_one({'name': course_name})
        if course and entered_password == course.get('password'):
            mycourses_collection.insert_one({
                'user_email': user_email,
                'course_name': course_name,
                'created_by': course.get('createdBy'),
                'description': course.get('description')
            })
            print("Redirecting to mycourses/student")
            return redirect('/mycourses/student')
        print("Redirecting to login page")
    return redirect(url_for('role'))

@app.route('/course/<course_name>', methods=['GET'])
def individual_course(course_name):
    user_email = session.get('email') or session.get('student_email')
    joined_course = mycourses_collection.find_one({
        'user_email': user_email,
        'course_name': course_name
    })
    if not joined_course:
        return redirect(url_for('student_courses'))
    recommendation_data = recommendation_collection.find_one({'user_id': user_email})
    recommendation_result = recommendation_data.get('recommendation') if recommendation_data else None
    if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
        return render_template('individual_course_horror.html', course=joined_course)
    elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
        return render_template('individual_course_nature.html', course=joined_course)
    else:
        return render_template('individual_course_fantasy.html', course=joined_course)

def get_quizzes(course_name):
    quiz_collection = db['quiz']
    return list(quiz_collection.find({'course_name': course_name}))

def get_completed_quizzes(user_email, course_name):
    completed_quiz_collection = db['quizsubmission']
    return list(completed_quiz_collection.find({
        'user_email': user_email,
        'course_name': course_name
    }))

def get_recommendation_result(user_email):
    recommendation_data = recommendation_collection.find_one({'user_id': user_email})
    return recommendation_data.get('recommendation') if recommendation_data else None

@app.route('/see_quizzes/<course_name>', methods=['GET'])
def see_quizzes(course_name):
    course_quizzes = get_quizzes(course_name)
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email  
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    completed_tests = get_completed_quizzes(user_email, course_name)
    non_completed_tests = [quiz for quiz in course_quizzes if quiz['quiz_name'] not in [completed_quiz['quiz_name'] for completed_quiz in completed_tests]]
    recommendation_result = get_recommendation_result(user_email)
    if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
        return render_template('student_quizzes_horror.html', course_name=course_name, completed_tests=completed_tests, non_completed_tests=non_completed_tests)
    elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
        return render_template('student_quizzes_nature.html', course_name=course_name, completed_tests=completed_tests, non_completed_tests=non_completed_tests)
    else:
        return render_template('student_quizzes_fantasy.html', course_name=course_name, completed_tests=completed_tests, non_completed_tests=non_completed_tests)

def get_user_recommendation_result(user_email):
    recommendation_data = recommendation_collection.find_one({'user_id': user_email})
    return recommendation_data.get('recommendation') if recommendation_data else None

quiz_start_time = datetime.now()

@app.route('/start_quiz/<course_name>/<quiz_name>', methods=['GET', 'POST'])
def start_quiz(course_name, quiz_name):
    global quiz_start_time
    user_email = session.get('email') or session.get('student_email')
    recommendation_result = get_user_recommendation_result(user_email)
    if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
        template_name = 'enter_quizzes_horror.html'
    elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
        template_name = 'enter_quizzes_nature.html'
    else:
        template_name = 'enter_quizzes_fantasy.html'
    user_answers = []
    quiz_collection = db['quiz']
    quiz = quiz_collection.find_one({'course_name': course_name, 'quiz_name': quiz_name})
    questions = quiz.get('questions', [])
    timer = quiz.get('timer', 0)
    student_collection = db['student']
    new_collection = db['new_users']
    new_datas = new_collection.find_one({'email': user_email})
    student_data = student_collection.find_one({'email': user_email})
    students_collection = db['students']
    second_time = students_collection.find_one({'email': user_email})
    students_data = students_collection.find_one({'email': user_email})
    slow_collection = db['slow_learners']
    slow_data = slow_collection.find_one({'email': user_email})
    total_coins = student_data.get('total_coins', 0)
    total_keys = student_data.get('total_keys', 0)
    total_heart = student_data.get('total_heart', 0)
    if quiz is None:
        return "Quiz not found"
    if request.method == 'POST':
        user_answers = {question: request.form.get(question) for question in request.form}
        print('user_answers are', user_answers)
        # 1) Total Marks
        total_marks = 0
        for i, question in enumerate(questions):
            question_key = f'question_{i}'
            if question_key in user_answers and user_answers[question_key] == question['correct_answer']:
                total_marks += 1
        print('total marks', total_marks)
        # 2) Time Taken to Submit Quiz
        if quiz_start_time:
            quiz_end_time = datetime.now()
            time_taken = (quiz_end_time - quiz_start_time).seconds
            print('Time taken to submit quiz:', time_taken, 'seconds')
        # 3) Highest Incorrect Type
        incorrect_types = {'conceptual': 0, 'application': 0, 'problem solving': 0}
        for i, question in enumerate(questions):
            question_key = f'question_{i}'
            if question_key in user_answers and user_answers[question_key] != question['correct_answer']:
                incorrect_types[question['type']] += 1
        highest_incorrect_type = max(incorrect_types, key=incorrect_types.get)
        print('Highest Incorrect Type:', highest_incorrect_type)
        # 4) Correct Ratio
        correct_ratio = total_marks / len(questions)
        print('Correct Ratio:', correct_ratio)
        # 5) Incorrect Ratio
        incorrect_ratio = 1 - correct_ratio
        print('Incorrect Ratio:', incorrect_ratio)
        if slow_data is None and new_datas is not None and total_marks <= quiz['condition_marks']:
            print("Condition 1: slow_data is None and new_datas is not None and total_marks < quiz['condition_marks']")
            new_collection.delete_one({'email': user_email})
            user_type = 'slow learner'
            slow_collection.insert_one({
                'email': user_email,
                'learning_level': user_type,
                'correct_ratio': correct_ratio,
                'total_marks': total_marks,
                'incorrect_type': highest_incorrect_type,
                'total_time_taken': time_taken,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')
            })
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins,
                          'total_heart': total_heart,
                          'total_keys': total_keys}}
            )
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':user_type}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('retry_horror', course_name=course_name, quiz_name=quiz_name))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('retry_nature', course_name=course_name, quiz_name=quiz_name))
            else:
                return redirect(url_for('retry_fantasy', course_name=course_name, quiz_name=quiz_name))

        elif new_datas is not None and slow_data is None and  total_marks > quiz['condition_marks']:
            print("Condition 2: new_datas is not None and total_marks > quiz['condition_marks']")
            new_collection.delete_one({'email': user_email})
            if correct_ratio > 0.85:
                user_type = 'quick learner'
            elif 0.81 <= correct_ratio <= 0.84:
                user_type = 'average learner'
            else:
                user_type = 'slow learner'
            students_collection.insert_one({
                'email': user_email,
                'learning_level': user_type,
                'correct_ratio': correct_ratio,
                'total_marks': total_marks,
                'highest_incorrect_type': highest_incorrect_type,
                'time_taken': time_taken,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')
            })
            leaderboard_collection.insert_one({
                'email': user_email,
                'learning_level': user_type,
                'total_marks': total_marks,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')
            })
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':user_type}}
            )
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins+100,
                        'total_heart': total_heart+2,
                        'total_keys': total_keys+1}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('quiz_result_horror', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('quiz_result_nature', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            else:
                return redirect(url_for('quiz_result_fantasy', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
        elif slow_data is not None and second_time is None and new_datas is None and  total_marks <= quiz['condition_marks']:
            print("condition no 3 is taking to action")
            slow_collection.update_one(
                {'email': user_email},
                {
                    '$set': {
                        'learning_level':'slow learner',
                        'correct_ratio': correct_ratio,
                        'total_marks': total_marks,
                        'incorrect_type': highest_incorrect_type,
                        'course_name': course_name,
                        'quiz_name': quiz_name,
                        'total_time_taken': time_taken,
                        'submission_date': datetime.now().strftime('%Y-%m-%d')
                    }
                }
            )
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':'slow learner'}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('retry_horror', course_name=course_name, quiz_name=quiz_name))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('retry_nature', course_name=course_name, quiz_name=quiz_name))
            else:
                return redirect(url_for('retry_fantasy', course_name=course_name, quiz_name=quiz_name))

        elif second_time is  not None and slow_data is  not None and new_datas is None and  total_marks <= quiz['condition_marks']:
            print("Condition 4: is incoming")
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins,
                        'total_heart': total_heart,
                        'total_keys': total_keys}}
            )
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':'slow learner'}}
            )
            slow_collection.update_one(
                {'email': user_email},
                {
                    '$set': {
                        'learning_level': 'slow learner',
                        'correct_ratio': correct_ratio,
                        'total_marks': total_marks,
                        'incorrect_type': highest_incorrect_type,
                        'course_name': course_name,
                        'quiz_name': quiz_name,
                        'total_time_taken': time_taken,
                        'submission_date': datetime.now().strftime('%Y-%m-%d')
                    }
                }
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('retry_horror', course_name=course_name, quiz_name=quiz_name))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('retry_nature', course_name=course_name, quiz_name=quiz_name))
            else:
                return redirect(url_for('retry_fantasy', course_name=course_name, quiz_name=quiz_name))    
        elif slow_data is not None and second_time is None and new_datas is None and  total_marks > quiz['condition_marks']:
            print("Condition 5 : is incoming")
            slow_collection.delete_one({'email': user_email})
            if correct_ratio > 0.85:
                user_type = 'quick learner'
            elif 0.81 <= correct_ratio <= 0.84:
                user_type = 'average learner'
            else:
                user_type = 'slow learner'

            students_collection.insert_one({
                'email': user_email,
                'learning_level': user_type,
                'correct_ratio': correct_ratio,
                'total_marks': total_marks,
                'highest_incorrect_type': highest_incorrect_type,
                'time_taken': time_taken,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')
            })
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins+100,
                          'total_heart': total_heart+2,
                          'total_keys': total_keys+1}}
            )
            leaderboard_collection.insert_one({
                'email': user_email,
                'learning_level': user_type,
                'total_marks': total_marks,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')
            })
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':user_type}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('quiz_result_horror', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('quiz_result_nature', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            else:
                return redirect(url_for('quiz_result_fantasy', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
        elif second_time is  not None and slow_data is  not None and new_datas is None and  total_marks > quiz['condition_marks']:
            print("condition 6 is cming")
            slow_collection.delete_one({'email': user_email})
            result = subprocess.check_output(["python", "model_predictor.py", str(correct_ratio), highest_incorrect_type, str(time_taken)])
            predicted_learning_level = result.decode('utf-8').strip().split(":")[-1].strip()
            print('predicted_learning_level:', predicted_learning_level)
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins+100,
                        'total_heart': total_heart+2,
                        'total_keys': total_keys+1}}
            )
            students_collection.insert_one({
                'email': user_email,
                'learning_level': predicted_learning_level,
                'correct_ratio': correct_ratio,
                'total_marks': total_marks,
                'highest_incorrect_type': highest_incorrect_type,
                'time_taken': time_taken,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')

            })
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':predicted_learning_level}}
            )
            leaderboard_collection.insert_one({
                'email': user_email,
                'learning_level': predicted_learning_level,
                'total_marks': total_marks,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')

            })
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('quiz_result_horror', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('quiz_result_nature', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            else:
                return redirect(url_for('quiz_result_fantasy', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
        elif second_time is not None and slow_data is None and  total_marks <= quiz['condition_marks']:
            print("Condition 7: take place")
            user_type='slow learner'
            slow_collection.insert_one({
                'email': user_email,
                'learning_level': user_type,
                'correct_ratio': correct_ratio,
                'total_marks': total_marks,
                'incorrect_type': highest_incorrect_type,
                'total_time_taken': time_taken,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')
            })
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins,
                        'total_heart': total_heart,
                        'total_keys': total_keys}}
            )
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':user_type}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('retry_horror', course_name=course_name, quiz_name=quiz_name))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('retry_nature', course_name=course_name, quiz_name=quiz_name))
            else:
                return redirect(url_for('retry_fantasy', course_name=course_name, quiz_name=quiz_name))
        elif second_time is not None and slow_data is None and  total_marks > quiz['condition_marks']:
            print("condition 8: is incoming")
            result = subprocess.check_output(["python", "model_predictor.py", str(correct_ratio), highest_incorrect_type, str(time_taken)])
            predicted_learning_level = result.decode('utf-8').strip()
            print('predicted_learning_level:', predicted_learning_level)
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins+100,
                        'total_heart': total_heart+2,
                        'total_keys': total_keys+1}}
            )
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':predicted_learning_level}}
            )
            students_collection.insert_one({
                'email': user_email,
                'learning_level': predicted_learning_level,
                'correct_ratio': correct_ratio,
                'total_marks': total_marks,
                'highest_incorrect_type': highest_incorrect_type,
                'time_taken': time_taken,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')

            })
            leaderboard_collection.insert_one({
                'email': user_email,
                'learning_level': predicted_learning_level,
                'total_marks': total_marks,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d')

            })
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('quiz_result_horror', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('quiz_result_nature', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            else:
                return redirect(url_for('quiz_result_fantasy', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio)) 
    if quiz_start_time is None:
        quiz_start_time = datetime.now()
    return render_template(template_name, course_name=course_name, quiz_name=quiz_name, questions=questions, timer=timer, user_answers=user_answers, total_coins=total_coins, total_keys=total_keys, total_heart=total_heart)

@app.route('/quiz_result_horror/<course_name>/<quiz_name>/<total_marks>/<correct_ratio>/<incorrect_ratio>', methods=['GET'])
def quiz_result_horror(course_name, quiz_name, total_marks, correct_ratio, incorrect_ratio):
    return render_template('quiz_result_horror.html', course_name=course_name, quiz_name=quiz_name, result='horror', total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio)

@app.route('/quiz_result_nature/<course_name>/<quiz_name>/<total_marks>/<correct_ratio>/<incorrect_ratio>', methods=['GET'])
def quiz_result_nature(course_name, quiz_name, total_marks, correct_ratio, incorrect_ratio):
    return render_template('quiz_result_nature.html', course_name=course_name, quiz_name=quiz_name, result='nature', total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio)

@app.route('/quiz_result_fantasy/<course_name>/<quiz_name>/<total_marks>/<correct_ratio>/<incorrect_ratio>', methods=['GET'])
def quiz_result_fantasy(course_name, quiz_name, total_marks, correct_ratio, incorrect_ratio):
    return render_template('quiz_result_fantasy.html', course_name=course_name, quiz_name=quiz_name, result='fantasy', total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio)

@app.route('/assignment_list/<course_name>/<quiz_name>', methods=['GET'])
def assignment_list(course_name, quiz_name):
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email  
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    assignment_collection = db['assignment']
    assignments = assignment_collection.find({
        'course_name': course_name,
        'quiz_name': quiz_name
    })
    recommendation_result = get_user_recommendation_result(user_email)  # Replace with your actual logic to get recommendation result
    if assignments:
        if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
            return render_template('assignment_list_horror.html', course_name=course_name, quiz_name=quiz_name, assignments=assignments)
        elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
            return render_template('assignment_list_nature.html', course_name=course_name, quiz_name=quiz_name, assignments=assignments)
        elif recommendation_result == 'based on above we recommend you fantasy theme to nourish and to grow':
            return render_template('assignment_list_fantasy.html', course_name=course_name, quiz_name=quiz_name, assignments=assignments)
    else:
        return render_template('assignment_not_found.html')

@app.route('/fill_assignment/<course_name>/<quiz_name>/<assignment_name>', methods=['GET'])
def fill_assignment(course_name, quiz_name, assignment_name):
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email  
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    recommendation_result = get_user_recommendation_result(user_email)  # Replace with your actual logic to get recommendation result
    assignment_collection = db['assignment']
    assignment = assignment_collection.find_one({
        'course_name': course_name,
        'quiz_name': quiz_name,
        'assignment_name': assignment_name
    })
    if assignment:
        second_time = students_collection.find_one({'email': user_email})
        learning_level = second_time['learning_level'] if second_time else None
        questions = assignment.get('questions', [])
        filtered_questions = []
        for question in questions:
            if learning_level == 'quick learner' and question['difficulty_level'] == 'hard':
                filtered_questions.append(question)
            elif learning_level == 'average learner' and question['difficulty_level'] == 'medium':
                filtered_questions.append(question)
            elif learning_level == 'slow learner' and question['difficulty_level'] == 'easy':
                filtered_questions.append(question)
        if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
            return render_template('fill_assignment_horror.html', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name, questions=filtered_questions)
        elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
            return render_template('fill_assignment_nature.html', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name, questions=filtered_questions)
        elif recommendation_result == 'based on above we recommend you fantasy theme to nourish and to grow':
            return render_template('fill_assignment_fantasy.html', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name, questions=filtered_questions)
    else:
        return render_template('assignment_not_found.html')

@app.route('/completed_assignment/<course_name>/<quiz_name>/<assignment_name>', methods=['POST'])
def completed_assignment(course_name, quiz_name,assignment_name):
    user_email = session.get('email') or session.get('student_email')
    assignment_collection = db['assignment']
    assignment = assignment_collection.find_one({'course_name': course_name, 'quiz_name': quiz_name})
    if assignment:
        questions = assignment.get('questions', [])
        for question in questions:
            answer_key = f'answer_{questions.index(question) + 1}'
            user_answer = request.form.get(answer_key)
            students_assignment.insert_one({
                'user_email': user_email,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'question': question['question'],
                'user_answer': user_answer,
                'assignment_name':assignment_name
            })
            student_test_collection.insert_one({
                'user_email': user_email,
                'course_name': course_name,
                'quiz_name': quiz_name,
                'email':user_email,
                'assignment_name':assignment_name
                
            })
        return redirect(url_for('role'))

@app.route('/see_assignments/<course_name>', methods=['GET'])
def see_assignments(course_name):
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email if email else student_email
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    course_quizzes = list(quiz_collection.find({'course_name': course_name}))
    recommendation_data = recommendation_collection.find_one({'user_id': user_email})
    recommendation_result = recommendation_data.get('recommendation') if recommendation_data else None
    if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
        return render_template('student_assignment_quiz_horror.html', course_name=course_name, quizzes=course_quizzes)
    elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
        return render_template('student_assignment_quiz_nature.html', course_name=course_name, quizzes=course_quizzes)
    else:
        return render_template('student_assignment_quiz_fantasy.html', course_name=course_name, quizzes=course_quizzes)


@app.route('/assignment_array/<course_name>/<quiz_name>', methods=['GET'])
def assignment_array(course_name, quiz_name):
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email if email else student_email
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    assignment_collection = db['assignment']
    assignments = assignment_collection.find({
        'course_name': course_name,
        'quiz_name': quiz_name
    })
    recommendation_result = get_user_recommendation_result(user_email)  # Replace with your actual logic to get recommendation result
    if assignments:
        if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
            return render_template('assignment_array_horror.html', course_name=course_name, quiz_name=quiz_name, assignments=assignments)
        elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
            return render_template('assignment_array_nature.html', course_name=course_name, quiz_name=quiz_name, assignments=assignments)
        elif recommendation_result == 'based on above we recommend you fantasy theme to nourish and to grow':
            return render_template('assignment_array_fantasy.html', course_name=course_name, quiz_name=quiz_name, assignments=assignments)
    else:
        return render_template('assignment_not_found.html')

@app.route('/watch_assignment/<course_name>/<quiz_name>/<assignment_name>', methods=['GET'])
def watch_assignment(course_name, quiz_name, assignment_name):
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email  
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    recommendation_result = get_user_recommendation_result(user_email)  
    assignment = students_assignment.find_one({
        'course_name': course_name,
        'quiz_name': quiz_name,
        'assignment_name': assignment_name
    })
    if assignment:
        user_answers = assignment.get('user_answer', '')
        assessment_mark = assignment.get('assessment_mark', '')
        print("Assessment Mark:", assessment_mark)
        question = assignment.get('question', '')
        user_answers_list = user_answers.split('\n')
        if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
            return render_template('watch_assignment_horror.html', user_answers=user_answers_list, assessment_mark=assessment_mark,question=question)
        elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
            return render_template('watch_assignment_nature.html', user_answers=user_answers_list, assessment_mark=assessment_mark,question=question)
        elif recommendation_result == 'based on above we recommend you fantasy theme to nourish and to grow':
            return render_template('watch_assignment_fantasy.html', user_answers=user_answers_list, assessment_mark=assessment_mark,question=question)

@app.route('/see_materials/<course_name>', methods=['GET'])
def see_materials(course_name):
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email if email else student_email
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    course_quizzes = list(quiz_collection.find({'course_name': course_name}))
    recommendation_data = recommendation_collection.find_one({'user_id': user_email})
    recommendation_result = recommendation_data.get('recommendation') if recommendation_data else None
    if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
        return render_template('student_quiz_materials_horror.html', course_name=course_name, quizzes=course_quizzes)
    elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
        return render_template('student_quiz_materials_nature.html', course_name=course_name, quizzes=course_quizzes)
    else:
        return render_template('student_quiz_materials_fantasy.html', course_name=course_name, quizzes=course_quizzes)

@app.route('/view_materials/<course_name>/<quiz_name>', methods=['GET'])
def view_materials(course_name, quiz_name):
    if 'email' in session and 'student_email' in session:
        email = session['email']
        student_email = session['student_email']
        user_email = email if email else student_email
    elif 'email' in session:
        user_email = session['email']
    elif 'student_email' in session:
        user_email = session['student_email']
    else:
        return redirect('/role')
    material_collection= db['material_collection']
    print('going to slow_data')
    material_data = material_collection.find_one({'course_name': course_name, 'quiz_name': quiz_name})
    print(f"Material Data: {material_data}")  
    learning_level_document = learning_collection.find_one({'email': user_email}, {'learning_level': 1, '_id': 0})
    if learning_level_document:
        user_learning_level = learning_level_document.get('learning_level')
        print(user_learning_level)
        recommendation_data = recommendation_collection.find_one({'user_id': user_email})
        recommendation_result = recommendation_data.get('recommendation') if recommendation_data else None
        if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
            return render_template('view_materials_quiz_horror.html', course_name=course_name, quiz_name=quiz_name,materials=material_data, learning_level=user_learning_level)

        elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
            return render_template('view_materials_quiz_nature.html', course_name=course_name, quiz_name=quiz_name, materials=material_data, learning_level=user_learning_level)
        else:
            return render_template('view_materials_quiz_fantasy.html', course_name=course_name, quiz_name=quiz_name, materials=material_data, learning_level=user_learning_level)
        
@app.route('/retry_horror/<course_name>/<quiz_name>')
def retry_horror(course_name, quiz_name):
    return render_template('retry_horror.html', course_name=course_name, quiz_name=quiz_name)

@app.route('/retry_horror/<course_name>/<quiz_name>')
def retry_nature(course_name, quiz_name):
    return render_template('retry_nature.html', course_name=course_name, quiz_name=quiz_name)

@app.route('/retry_horror/<course_name>/<quiz_name>')
def retry_fantasy(course_name, quiz_name):
    return render_template('retry_fantasy.html',course_name=course_name, quiz_name=quiz_name)        

#----------------------------------------<Teacher>------------------------------------------------------------------------------------
@app.route('/check_pin', methods=['POST'])
def check_pin():
    entered_pin = request.form.get('pin')
    if entered_pin == '123456':
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid PIN'})

@app.route('/teacherregister', methods=['GET', 'POST'])
def teacher_register():
    if request.method == 'POST':
        name = request.form.get('name')
        register_number = request.form.get('register_number')
        roll_number = request.form.get('roll_number')
        department = request.form.get('department')
        email_id = request.form.get('email_id')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not email_id.endswith('tce.edu'):
            flash('Invalid email format')
            return redirect('/teacherregister')
        existing_user = teacher_collection.find_one({'email_id': email_id})
        if existing_user:
            flash('Email already exists')
            return redirect('/teacherregister')
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect('/teacherregister')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {
            'name': name,
            'register_number': register_number,
            'roll_number': roll_number,
            'department': department,
            'email_id': email_id,
            'password': hashed_password,
            'role': 'teacher',
        }
        result = teacher_collection.insert_one(user_data)
        if result.inserted_id:
            session['email_id'] = email_id
            session['department'] = department
            flash('Registration successful! You can now log in.')
            return redirect('/teacherdashboard')
    return render_template('teacherregister.html')

@app.route('/teacherlogin', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print(f"Received login request for email: {email}")
        teacher = teacher_collection.find_one({'email_id': email, 'role': 'teacher'})
        if teacher and bcrypt.checkpw(password.encode('utf-8'), teacher['password']):
            session['teacher_email'] = email
            print("Login successful. Redirecting to teacherdashboard.")
            return redirect('/teacherdashboard')
    return render_template('teacherlogin.html')

@app.route('/teacherdashboard')
def teacherdashboard():
    if 'email_id' in session or 'teacher_email' in session:
        emails_list = [session.get('email_id'), session.get('teacher_email')]
        for email in emails_list:
            if email:
                teacher_data = teacher_collection.find_one({'email_id': email})
                if teacher_data:    
                    template_context = {
                        'name': teacher_data['name'],
                        'role': teacher_data['role'],
                        'email_id': teacher_data['email_id'],
                        'department': teacher_data['department'],
                    }
                    return render_template('teacherdashboard.html', teacher_data=template_context)
    return redirect(url_for('teacher_login'))

@app.route("/leaderboard", methods=["GET", "POST"])
def leaderboard():
    unique_courses, unique_quiz_names, unique_assignments = get_unique_options()
    if request.method == "POST":
        course_name = request.form.get("course_name")
        quiz_name = request.form.get("quiz_name")
        assignment_name = request.form.get("assignment_name")
        print(f"course_name: {course_name}, quiz_name: {quiz_name}, assignment_name: {assignment_name}")
        data = list(
            collection.find(
                {
                    "course_name": course_name,
                    "quiz_name": quiz_name,
                    "assignment": assignment_name,
                }
            )
        )
        print("Fetched data:", data)
        return render_template("leaderboard.html",data=data,unique_courses=unique_courses,unique_quiz_names=unique_quiz_names,unique_assignments=unique_assignments)
    return render_template("leaderboard.html", unique_courses=unique_courses, unique_quiz_names=unique_quiz_names, unique_assignments=unique_assignments)

@app.route("/save_mark", methods=["POST"])
def save_mark():
    data = request.json
    user_email = data["userEmail"]
    mark = data["mark"]
    collection.update_one({"user_email": user_email}, {"$set": {"assessment_mark": mark}}, upsert=True)
    return jsonify({"status": "success"})

@app.route('/mycourses')
def my_courses():
    if 'email_id' in session or 'teacher_email' in session:
        emails_list = [session.get('email_id'), session.get('teacher_email')]
        for teacher_email in emails_list:
            if teacher_email:
                teacher_data = teacher_collection.find_one({'email_id': teacher_email})
                if teacher_data:
                    department = teacher_data['department']
                    teacher_courses = list(courses_collection.find({'createdBy': teacher_email, 'department': department}))
                    department_courses = list(courses_collection.find({
                        'department': department,
                        'createdBy': {'$ne': teacher_email}
                    }))
                    return render_template('mycourses.html', teacher_courses=teacher_courses, department_courses=department_courses)
    return redirect(url_for('teacherlogin'))

@app.route('/course_attributes/<course_name>')
def course_attributes(course_name):
    if 'teacher_email' in session:
        teacher_email = session.get('teacher_email')
        course = courses_collection.find_one({'name': course_name, 'createdBy': teacher_email})
        if course:
            return render_template('course_attributes.html', course=course)
        else:
            return redirect(url_for('mycourses'))
    return redirect(url_for('teacherlogin'))

@app.route('/view_quiz/<course_name>')
def view_quiz(course_name):
    quizzes = quiz_collection.find({'course_name': course_name})
    print('quizzes:',quizzes)
    print('course_name',course_name)
    return render_template('view_quiz.html', course_name=course_name, quizzes=quizzes)

@app.route('/edit_quiz/<quiz_name>/<course_name>', methods=['GET', 'POST'])
def edit_quiz(quiz_name, course_name):
    quiz = quiz_collection.find_one({'quiz_name': quiz_name})
    if not quiz:
        print(f"Quiz not found for quiz_name: {quiz_name}")
        return render_template('quiz_not_found.html')
    if request.method == 'POST':
        try:
            print("POST request received")
            print("Form data:", request.form)
            updated_data = {
                "course_name": course_name,
                "quiz_name": request.form['quiz_name'],
                "timer": int(request.form['timer']),
                "condition_marks": int(request.form['condition_marks']),
                "badges": request.form['badges'],
                "questions": []
            }
            question_keys = [key for key in request.form.keys() if key.startswith('question_')]
            for key in question_keys:
                question_index = key.split('_')[-1]
                question = {
                    "question": request.form[f'question_{question_index}'],
                    "choices": request.form.getlist(f'choices_{question_index}[]'),
                    "correct_answer": request.form[f'correctAnswer_{question_index}'],
                    "hint": request.form[f'hint_{question_index}'],
                    "type": request.form[f'type_{question_index}']
                }
                updated_data["questions"].append(question)
            print("Updated quiz data:", updated_data)
            result = quiz_collection.update_one({'quiz_name': quiz_name}, {'$set': updated_data})
            if result.modified_count > 0:
                print("Quiz updated successfully")
                return redirect(url_for('course_attributes', course_name=course_name))
            else:
                print("Quiz update failed")
                return render_template('quiz_update_failed.html')

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return render_template('error.html')
    return render_template('edit_quiz.html', quiz=quiz, course_name=course_name)

@app.route('/show_quiz/<course_name>')
def show_quiz(course_name):
    quizzes = quiz_collection.find({'course_name': course_name}, {'quiz_name': 1, '_id': 0})
    return render_template('show_quiz.html', course_name=course_name, quizzes=quizzes)

@app.route('/view_assignment/<course_name>/<quiz_name>')
def view_assignment(course_name, quiz_name):
    assignments = assignment_collection.find({'course_name': course_name, 'quiz_name': quiz_name})
    return render_template('view_assignment.html', assignments=assignments)

@app.route("/show_materials/<course_name>")
def show_materials(course_name):
    quizzes = quiz_collection.find({"course_name": course_name}, {"quiz_name": 1, "_id": 0})
    return render_template("show_materials.html", course_name=course_name, quizzes=quizzes)

@app.route("/view_materials_teacher/<course_name>/<quiz_name>", methods=["GET", "POST"])
def view_materials_teacher(course_name, quiz_name):
    material = material_collection.find_one({"course_name": course_name, "quiz_name": quiz_name})
    if material:
        return render_template("view_materials_teacher.html", material=material)
    else:
        return render_template("error.html", message="Material not found")

@app.route('/edit_assignment/<assignment_name>', methods=['GET', 'POST'])
def edit_assignment(assignment_name):
    assignment = assignment_collection.find_one({'assignment_name': assignment_name})
    if request.method == 'POST':
        updated_data = {
            "assignment_name": request.form['assignmentName'],
            "questions": []
        }
        question_keys = [key for key in request.form.keys() if key.startswith('question_')]
        for key in question_keys:
            question_index = key.split('_')[-1]
            question = {
                "question": request.form[f'question_{question_index}']
            }
            updated_data["questions"].append(question)
        result = assignment_collection.update_one({'assignment_name': assignment_name}, {'$set': updated_data})
        if result.modified_count > 0:
            return redirect(url_for('course_attributes', course_name=assignment['course_name']))
    return render_template('edit_assignment.html', assignment=assignment)

@app.route('/createcourse', methods=['GET', 'POST'])
def create_course():
    if 'email_id' in session or 'teacher_email' in session:
        emails_list = [session.get('email_id'), session.get('teacher_email')]
        for teacher_email in emails_list:
            if teacher_email:
                teacher_data = teacher_collection.find_one({'email_id': teacher_email})
                if teacher_data and 'department' in teacher_data:
                    department = teacher_data['department']
                    if request.method == 'POST':
                        name = request.form['title']
                        description = request.form['description']
                        code= request.form['code']
                        print('title',name)
                        print('description',description)
                        print('password',code)
                        print('createdBy',teacher_email)
                        print('department',department)
                        new_course = {
                            'name': name,
                            'department': department,
                            'createdBy': teacher_email,
                            'description': description,
                            'password': code
                        }
                        session['name'] = name
                        print('session',session)
                        result = courses_collection.insert_one(new_course)
                        if result.inserted_id:
                            return redirect('/coursepage')  
                        else:
                            return render_template('createcourse.html', message='Failed to create the course')
                    return render_template('createcourse.html')
        return redirect(url_for('teacherlogin'))
    return redirect(url_for('teacherlogin'))

@app.route('/coursepage',methods=['GET', 'POST'])
def coursepage():
    if request.method == 'POST':
        course_type = request.form.get('course_type')
        if course_type == 'assignment':
            return redirect('/submit_assignment')
        elif course_type == 'quiz':
            return redirect('/submit_quiz')
        else:
            return render_template('createcourse.html', message='Invalid course type')    
    return render_template('coursepage.html')

@app.route('/submit_quiz', methods=['GET', 'POST'])
def submit_quiz():
    success_message = None
    if request.method == 'POST':
        if 'email_id' in session or 'teacher_email' in session or 'name' in session:
            emails_list = [session.get('email_id'), session.get('teacher_email')]
            name = session.get('name')
            for teacher_email in emails_list:
                if teacher_email:
                    teacher_data = teacher_collection.find_one({'email_id': teacher_email})
                    quiz_name = request.form['quizName']
                    quiz_data = {
                        "course_name": name,
                        "quiz_name": quiz_name,
                        "timer": int(request.form['timer']),
                        "condition_marks": int(request.form['mark']),
                        "badges": request.form['badges'],
                        "questions": []
                    }
                    session['quiz_name'] = quiz_name
                    question_keys = [key for key in request.form.keys() if key.startswith('question_')]
                    for key in question_keys:
                        question_index = key.split('_')[-1]
                        question = {
                            "question": request.form[f'question_{question_index}'],
                            "choices": request.form.getlist(f'choices_{question_index}[]'),
                            "correct_answer": request.form[f'correctAnswer_{question_index}'],
                            "hint": request.form[f'hint_{question_index}'],
                            "type": request.form[f'type_{question_index}']
                        }
                        quiz_data["questions"].append(question)
                    result = quiz_collection.insert_one(quiz_data)
                    if result.inserted_id:
                        success_message = 'Quiz successfully inserted'
                    else:
                        success_message = 'Failed to insert the quiz'
    return render_template('submit_quiz.html', success_message=success_message)
    
@app.route('/submit_assignment', methods=['GET', 'POST'])
def submit_assignment():
    success_message = None
    if request.method == 'POST':
        if 'email_id' in session or 'teacher_email' in session or 'name' in session or 'quiz_name' in session:
            emails_list = [session.get('email_id'), session.get('teacher_email')]
            name = session.get('name')
            quiz_name = session.get('quiz_name')
            for teacher_email in emails_list:
                if teacher_email:
                    teacher_data = teacher_collection.find_one({'email_id': teacher_email})
                    assignment_data = {
                        "course_name": name,
                        "quiz_name": quiz_name,
                        "assignment_name": request.form.get('assignmentName'),
                        "questions": []
                    }
                    question_keys = [key for key in request.form.keys() if key.startswith('question_')]
                    for key in question_keys:
                        question_index = key.split('_')[-1]
                        question = {
                            "question": request.form[f'question_{question_index}'],
                            "difficulty_level": request.form[f'difficulty_{question_index}']
                        }
                        assignment_data["questions"].append(question)
                    result = assignment_collection.insert_one(assignment_data)
                    if result.inserted_id:
                        success_message = 'Assignment successfully submitted'
                    else:
                        success_message = 'Failed to insert the assignment'

    return render_template('submit_assignment.html', success_message=success_message)

@app.route("/submit_materials", methods=["GET", "POST"])
def submit_materials():
    success_message = None
    courses = []
    quizzes = []
    if (
        "email_id" in session
        or "teacher_email" in session
        or "name" in session
        or "quiz_name" in session
    ):
        emails_list = [session.get("email_id"), session.get("teacher_email")]
        name = session.get("name")
        quiz_name = session.get("quiz_name")

        for teacher_email in emails_list:
            if teacher_email:
                teacher_data = teacher_collection.find_one({"email_id": teacher_email})
                name = session.get("name")
                quiz_name = session.get("quiz_name")
        if request.method == "POST":
            course_name = name
            quiz_names = quiz_name
            slow_learner_material = request.form.get("slowLearnerMaterial")
            topper_material = request.form.get("topperMaterial")
            average_learner_material = request.form.get("averageLearnerMaterial")
            material_data = {
                "course_name": course_name,
                "quiz_name": quiz_names,
                "slow_learner_material": slow_learner_material,
                "topper_material": topper_material,
                "average_learner_material": average_learner_material,
            }
            result = material_collection.insert_one(material_data)
            if result.inserted_id:
                success_message = "Materials successfully assigned"
            else:
                success_message = "Failed to assign materials"
    return render_template("submit_materials.html", success_message=success_message)

@app.route('/give_quiz/<course_name>', methods=['GET', 'POST'])
def give_quiz(course_name):
    if request.method == 'POST':
        print("Form submitted successfully")
        quiz_name = request.form['quizName']
        course_name = request.form['coursename']
        quiz_data = {
            "course_name": course_name,
            "quiz_name": quiz_name,
            "timer": int(request.form['timer']),
            "condition_marks": int(request.form['mark']),
            "badges": request.form['badges'],
            "questions": []
        }
        question_keys = [key for key in request.form.keys() if key.startswith('question_')]
        for key in question_keys:
            question_index = key.split('_')[-1]
            question = {
                "question": request.form[f'question_{question_index}'],
                "choices": request.form.getlist(f'choices_{question_index}[]'),
                "correct_answer": request.form[f'correctAnswer_{question_index}'],
                "hint": request.form[f'hint_{question_index}'],
                "type": request.form[f'type_{question_index}']
            }
            quiz_data["questions"].append(question)
            print(f'Question {question_index}: {question}')
        result = quiz_collection.insert_one(quiz_data)
        if result.inserted_id:
            print("Quiz successfully inserted")
        else:
            print("Failed to insert the quiz")
        return redirect(url_for('completed'))
    return render_template('give_quiz.html')

@app.route('/completed')
def completed():
    return render_template('completed.html')

@app.route("/give_assignment/<course_name>", methods=["GET", "POST"])
def give_assignment(course_name):
    if request.method == "POST":
        assignment_name = request.form["assignmentName"]
        quiz_name = request.form["quizName"]
        questions = []
        question_keys = [key for key in request.form.keys() if key.startswith("question_")]
        for key in question_keys:
            question_index = key.split("_")[-1]
            question = {
                "question": request.form[f"question_{question_index}"],
                "difficulty": request.form[f"difficulty_{question_index}"],
            }
            questions.append(question)
            assignment_data = {
                "course_name": course_name,
                "assignment_name": assignment_name,
                "quiz_name": quiz_name,
                "questions": questions,
            }
            result = assignment_collection.insert_one(assignment_data)
        if result.inserted_id:
            return redirect(url_for("completed"))
        else:
            return render_template("error.html") 
    quizzes = quiz_collection.distinct("quiz_name", {"course_name": course_name})
    return render_template("give_assignment.html", course_name=course_name, quizzes=quizzes)

@app.route("/give_material/<course_name>", methods=["GET", "POST"])
def give_material(course_name):
    if request.method == "POST":
        material_link = request.form["materialLink"]
        quiz_name = request.form["quizName"]
        difficulty_level = request.form["difficulty_1"]
        material_data = {
            "course_name": course_name,
            "material_link": material_link,
            "quiz_name": quiz_name,
            "difficulty_level": difficulty_level,
        }
        result = material_collection.insert_one(material_data)
        if result.inserted_id:
            return redirect(url_for("completed"))
        else:
            return render_template("error.html") 
    quizzes = quiz_collection.distinct("quiz_name", {"course_name": course_name})
    return render_template("give_material.html", course_name=course_name, quizzes=quizzes)

@app.route("/tlogout")
def tlogout():
    session.clear()
    return redirect("/teacherlogin")

@app.route("/slogout")
def slogout():
    session.clear()
    return redirect("/studentlogin")

if __name__ == "__main__":
    app.debug = True
    app.run(port=5001)