from urllib.parse import quote_plus
import random
from flask import Flask, render_template, request, redirect, flash, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from flask_cors import CORS
import bcrypt  
import joblib
from flask import jsonify
from flask import render_template, redirect, session, send_from_directory
import numpy as np

from collections import Counter

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
collection = db["student_assignment"]
collection2 = db["assignment"]

CORS(app)

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
            'total_coins':250,
            'total_keys' :2,
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

collection3 = db.students
db = client.gamification
collection3 = db.students
collection4 = db.slow
collection5 = db.average
collection6 = db.quick
mycourses_collection = db.mycourses  # Adding mycourses collection

def fetch_leaderboard_data(user_email, course_name, quiz_name):
    try:
        # Fetch the learning level from the 'students' collection
        student_data = collection3.find_one({'email': user_email, 'course_name': course_name})
        learning_level = student_data.get('learning_level')

        # Fetch data for all learning levels
        quick_leaderboard_data = list(collection6.find({'quiz_name': quiz_name, 'course_name': course_name}))
        average_leaderboard_data = list(collection5.find({'quiz_name': quiz_name, 'course_name': course_name}))
        slow_leaderboard_data = list(collection4.find({'quiz_name': quiz_name, 'course_name': course_name}))

        # Check if the required fields exist
        if quick_leaderboard_data!=[]:
            # Convert MongoDB cursor to DataFrame
            quick_df = pd.DataFrame(quick_leaderboard_data)
            # Rank students based on total_marks
            quick_df['rank'] = quick_df['total_point'].rank(ascending=False, method='min')
            # Sort the DataFrame by rank
            quick_df = quick_df.sort_values(by='rank')
            # Highlight the row corresponding to the viewing student
            quick_df['highlight'] = quick_df['user_email'] == user_email

        if average_leaderboard_data!=[]:
            average_df = pd.DataFrame(average_leaderboard_data)
            average_df['rank'] = average_df['total_point'].rank(ascending=False, method='min')
            average_df = average_df.sort_values(by='rank')
            average_df['highlight'] = average_df['user_email'] == user_email

        if slow_leaderboard_data!=[]:
            slow_df = pd.DataFrame(slow_leaderboard_data)
            slow_df['rank'] = slow_df['total_point'].rank(ascending=False, method='min')
            slow_df = slow_df.sort_values(by='rank')
            slow_df['highlight'] = slow_df['user_email'] == user_email

        return (
            quick_df.to_dict(orient='records') if 'quick_df' in locals() else [],
            average_df.to_dict(orient='records') if 'average_df' in locals() else [],
            slow_df.to_dict(orient='records') if 'slow_df' in locals() else []
        )

    except Exception as e:
        raise ValueError(str(e))


@app.route('/<user_email>', methods=['GET', 'POST'])
def leaderboard(user_email):
    try:
        # Fetch the user's courses from the 'mycourses' collection
        user_courses_cursor = collection3.find({'email': user_email}, {'course_name': 1})
        user_courses = [doc['course_name'] for doc in user_courses_cursor]
        selected_course = None
        unique_quiz_names = []

        # Check if the form is submitted
        if request.method == 'POST':
            selected_course = request.form.get('course_name')
            selected_quiz = request.form.get('quiz_name')
            unique_quiz_names = collection3.distinct('quiz_name', {'course_name': selected_course})

            if selected_quiz is not None:
                # Fetch the data from the corresponding collection based on learning level and quiz name
                quick_leaderboard_data, average_leaderboard_data, slow_leaderboard_data = fetch_leaderboard_data(user_email, selected_course, selected_quiz)

                return render_template('leaderboard.html', user_email=user_email,
                                       unique_courses=user_courses, selected_course=selected_course,
                                       quick_leaderboard_data=quick_leaderboard_data,
                                       average_leaderboard_data=average_leaderboard_data,
                                       slow_leaderboard_data=slow_leaderboard_data,
                                       unique_quiz_names=unique_quiz_names, selected_quiz=selected_quiz)

        # On initial load, provide default values or handle as needed
        return render_template('leaderboard.html', user_email=user_email,
                               unique_courses=user_courses, selected_course=selected_course,
                               quick_leaderboard_data=[], average_leaderboard_data=[], slow_leaderboard_data=[],
                               unique_quiz_names=unique_quiz_names, selected_quiz=None)

    except Exception as e:
        # Handle the exception, log it, or return an error page
        return render_template('error.html', error=str(e))

# Add this endpoint to fetch quiz names dynamically
@app.route('/get_quiz_names/<user_email>', methods=['POST'])
def get_quiz_names(user_email):
    try:
        selected_course = request.form.get('course_name')
        unique_quiz_names = collection3.distinct('quiz_name', {'course_name': selected_course})

        return jsonify({'quiz_names': unique_quiz_names})

    except Exception as e:
        return jsonify({'error': str(e)})


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

@app.route("/see_quizzes/<course_name>", methods=["GET"])
def see_quizzes(course_name):
    course_quizzes = get_quizzes(course_name)

    # Initialize variables with default values
    user_email = None
    total_coins = 0

    if "email" in session and "student_email" in session:
        # Both emails are present, handle accordingly
        email = session["email"]
        student_email = session["student_email"]
        # Use one of them based on your logic
        user_email = email  # For example, use 'email'

        # Assuming you have a MongoDB connection and student_collection defined

    elif "email" in session:
        # Retrieve the user email from the session
        user_email = session["email"]
    elif "student_email" in session:
        # Retrieve the student email from the session
        user_email = session["student_email"]
    else:
        # Redirect to login if neither 'email' nor 'student_email' is in the session
        return redirect("/role")

    # Retrieve the user's coins from the database and store it in the session
    student_data = student_collection.find_one({"email": user_email})
    if student_data:
        total_coins = student_data.get("total_coins", 0)
        session["user_coins"] = total_coins

    # Get recommendation result based on user email
    recommendation_result = get_recommendation_result(user_email)

    print(f"Total coins for user {user_email}: {total_coins}")

    if (
        recommendation_result
        == "based on above we recommend you horror theme to nourish and to grow"
    ):
        return render_template(
            "student_quizzes_horror.html",
            course_name=course_name,
            course_quizzes=course_quizzes,
            total_coins=total_coins,
        )
    elif (
        recommendation_result
        == "based on above we recommend you nature content theme to nourish and to grow"
    ):
        return render_template(
            "student_quizzes_nature.html",
            course_name=course_name,
            course_quizzes=course_quizzes,
            total_coins=total_coins,
        )
    else:
        return render_template(
            "student_quizzes_fantasy.html",
            course_name=course_name,
            course_quizzes=course_quizzes,
            total_coins=total_coins,
)

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
    quiz_badges = quiz.get('badges', {})
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
    for question in questions:
        question_text = question.get('question', '')
        choices = question.get('choices', [])
        correct_answer = question.get('correct_answer', '')
        hint = question.get('hint', '')
        question_type = question.get('type', '')
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
                total_marks += 2
        print('total marks', total_marks)
        show_answer_clicks = int(request.form.get('showAnswerClickscount', 0))
        use_hint_clicks = request.form.get('useHintClicks', 0, type=int)
        add_extra_time_clicks = request.form.get('addExtraTimeClicks', 0, type=int)
        print('show_answer_clicks:',show_answer_clicks)
        print('use_hint_clicks:',use_hint_clicks)
        print('add_extra_time_clicks',add_extra_time_clicks)
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
            if correct_ratio > 0.80:
                user_type = 'quick learner'
            elif 0.50 <= correct_ratio <= 0.79:
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
                'submission_date': datetime.now().strftime('%Y-%m-%d'),
                'quiz_badges': quiz_badges,
                'add_extra_time clicks':add_extra_time_clicks,
                'use_hint_clicks':use_hint_clicks,
                'show_answer_clicks':show_answer_clicks
            })
            
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':user_type}}
            )
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins+50,
                        'total_heart': total_heart+2,
                        'total_keys': total_keys+1}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('quiz_result_horror', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio,quiz_badges=quiz_badges))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('quiz_result_nature', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio,quiz_badges=quiz_badges))
            else:
                return redirect(url_for('quiz_result_fantasy', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio,quiz_badges=quiz_badges))
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
            if correct_ratio > 0.80:
                user_type = 'quick learner'
            elif 0.50 <= correct_ratio <= 0.79:
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
                'submission_date': datetime.now().strftime('%Y-%m-%d'),
                'quiz_badges': quiz_badges,
                'add_extra_time clicks':add_extra_time_clicks,
                'use_hint_clicks':use_hint_clicks,
                'show_answer_clicks':show_answer_clicks
            })
            
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins+50,
                          'total_heart': total_heart+2,
                          'total_keys': total_keys+1}}
            )
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':user_type}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('quiz_result_horror', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio,quiz_badges=quiz_badges))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('quiz_result_nature', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio,quiz_badges=quiz_badges))
            else:
                return redirect(url_for('quiz_result_fantasy', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio,quiz_badges=quiz_badges))
        elif second_time is  not None and slow_data is  not None and new_datas is None and  total_marks > quiz['condition_marks']:
            print("condition 6 is cming")
            slow_collection.delete_one({'email': user_email})
            result = subprocess.check_output(["python", "model_predictor.py", str(correct_ratio), highest_incorrect_type, str(time_taken)])
            predicted_learning_level = result.decode('utf-8').strip().split(":")[-1].strip()
            print('predicted_learning_level:', predicted_learning_level)
            student_collection.update_one(
                {'email': user_email},
                {'$set': {'total_coins': total_coins+50,
                        'total_heart': total_heart+2,
                        'total_keys': total_keys+1}}
            )
            existing_record = students_collection.find_one({
                'email': user_email,
                'course_name': course_name,
                'quiz_name': quiz_name
            })

            if existing_record:
                # Update the existing record
                print("bro it is cming)")
                students_collection.update_one(
                    {
                        'email': user_email,
                        'course_name': course_name,
                        'quiz_name': quiz_name,
                    },
                    {
                        '$set': {
                            'learning_level': predicted_learning_level,
                            'correct_ratio': correct_ratio,
                            'total_marks': total_marks,
                            'highest_incorrect_type': highest_incorrect_type,
                            'time_taken': time_taken,
                            'submission_date': datetime.now().strftime('%Y-%m-%d'),
                            'quiz_badges': quiz_badges,
                            'add_extra_time clicks': add_extra_time_clicks,
                            'use_hint_clicks': use_hint_clicks,
                            'show_answer_clicks': show_answer_clicks
                        }
                    }
                )
            else:
                # Insert a new record
                print("TYAGA")
                students_collection.insert_one({
                    'email': user_email,
                    'learning_level': predicted_learning_level,
                    'correct_ratio': correct_ratio,
                    'total_marks': total_marks,
                    'highest_incorrect_type': highest_incorrect_type,
                    'time_taken': time_taken,
                    'course_name': course_name,
                    'quiz_name': quiz_name,
                    'submission_date': datetime.now().strftime('%Y-%m-%d'),
                    'quiz_badges': quiz_badges,
                    'add_extra_time clicks': add_extra_time_clicks,
                    'use_hint_clicks': use_hint_clicks,
                    'show_answer_clicks': show_answer_clicks
                })
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':predicted_learning_level}}
            )
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
                {'$set': {'total_coins': total_coins+50,
                        'total_heart': total_heart+2,
                        'total_keys': total_keys+1}}
            )
            existing_record = students_collection.find_one({
                'email': user_email,
                'course_name': course_name,
                'quiz_name': quiz_name
            })

            if existing_record:
                print("siuuu")
                # Update the existing record
                students_collection.update_one(
                    {
                        'email': user_email,
                        'course_name': course_name,
                        'quiz_name': quiz_name,
                    },
                    {
                        '$set': {
                            'learning_level': predicted_learning_level,
                            'correct_ratio': correct_ratio,
                            'total_marks': total_marks,
                            'highest_incorrect_type': highest_incorrect_type,
                            'time_taken': time_taken,
                            'submission_date': datetime.now().strftime('%Y-%m-%d'),
                            'quiz_badges': quiz_badges,
                            'add_extra_time clicks': add_extra_time_clicks,
                            'use_hint_clicks': use_hint_clicks,
                            'show_answer_clicks': show_answer_clicks
                        }
                    }
                )
            else:
                # Insert a new record
                print("ronaldoooo")
                students_collection.insert_one({
                    'email': user_email,
                    'learning_level': predicted_learning_level,
                    'correct_ratio': correct_ratio,
                    'total_marks': total_marks,
                    'highest_incorrect_type': highest_incorrect_type,
                    'time_taken': time_taken,
                    'course_name': course_name,
                    'quiz_name': quiz_name,
                    'submission_date': datetime.now().strftime('%Y-%m-%d'),
                    'quiz_badges': quiz_badges,
                    'add_extra_time clicks': add_extra_time_clicks,
                    'use_hint_clicks': use_hint_clicks,
                    'show_answer_clicks': show_answer_clicks
                })
            learning_collection.update_one(
                {'email': user_email},
                {'$set': {'learning_level':predicted_learning_level}}
            )
            if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
                return redirect(url_for('quiz_result_horror', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
                return redirect(url_for('quiz_result_nature', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio))
            else:
                return redirect(url_for('quiz_result_fantasy', course_name=course_name, quiz_name=quiz_name, total_marks=total_marks, correct_ratio=correct_ratio, incorrect_ratio=incorrect_ratio)) 
    if quiz_start_time is None:
        quiz_start_time = datetime.now() 
    return render_template(template_name, course_name=course_name, quiz_name=quiz_name, questions=questions, timer=timer, user_answers=user_answers, total_coins=total_coins, total_keys=total_keys, total_heart=total_heart,correct_answer=correct_answer,hint=hint)

def get_assignments(user_email, course_name, quiz_name):
    # Fetch assignments data dynamically from the database
    student_data = db.students.find_one(
        {
            'email': user_email,
            'course_name': course_name,
            'quiz_name': quiz_name
        }
    )

    # Check if student_data is not None and 'assignments' key is present
    if student_data and 'assignments' in student_data:
        # Prepare assignments dictionary from the 'assignments' field
        assignments_data = student_data['assignments']
        assignments = {assignment: {'completed': assignments_data[assignment].get('completed', False)} for assignment in assignments_data}
    else:
        assignments = {}
        
    print("Assignments Data:", list(assignments_data))    

    return assignments


def get_comparison_message(latest_submission, second_latest_submission):
    # Extracting click counts from the latest submission
    latest_add_extra_time_clicks = latest_submission.get('add_extra_time clicks', 0)
    latest_use_hint_clicks = latest_submission.get('use_hint_clicks', 0)
    latest_show_answer_clicks = latest_submission.get('show_answer_clicks', 0)

    # Extracting click counts from the second latest submission
    second_latest_add_extra_time_clicks = second_latest_submission.get('add_extra_time clicks', 0)
    second_latest_use_hint_clicks = second_latest_submission.get('use_hint_clicks', 0)
    second_latest_show_answer_clicks = second_latest_submission.get('show_answer_clicks', 0)

    # Compare the counts
    if (
        latest_add_extra_time_clicks > second_latest_add_extra_time_clicks or
        latest_use_hint_clicks > second_latest_use_hint_clicks or
        latest_show_answer_clicks > second_latest_show_answer_clicks
    ):
        return "Why are you using these options too much? Think, in the last tests, you used them very less."
    else:
        return "You are improving!"

@app.route('/quiz_result_horror/<course_name>/<quiz_name>/<total_marks>/<correct_ratio>/<incorrect_ratio>', methods=['GET'])
def quiz_result_horror(course_name, quiz_name, total_marks, correct_ratio, incorrect_ratio):
    user_email = session.get('email') or session.get('student_email')
    students_collection = db['students']
    quiz_collection = db['quiz']

    # Fetch details of the student's last two submissions for any quiz
    past_submissions = students_collection.find(
        {
            'email': user_email
        }
    ).sort('_id', -1).limit(2)
    # Convert the cursor to a list
    past_submissions_list = list(past_submissions)

    # Fetching quiz information from the quiz collection
    quiz_info = quiz_collection.find_one({'course_name': course_name, 'quiz_name': quiz_name})
    quiz_badge_names = quiz_info.get('badges', []) if quiz_info and 'badges' in quiz_info else []

    # Mapping of badge names to URLs based on stored data
    badge_data = {
        'pro': 'https://images.squarespace-cdn.com/content/v1/5ce4e383c91a190001537163/1653365043041-9SBNP4GHPLA1JXFSBKT7/Owl+5054+v6+Green+-+Black+-+600x600.gif',
        'intermediate': 'https://i.pinimg.com/originals/83/0e/f7/830ef72582287cfb5c7fbe61a24dbc36.gif',
        'beginner': 'https://cdn.dribbble.com/users/3278261/screenshots/6747984/ezgif.com-video-to-gif__11_.gif',
        # Add more mappings as needed
    }

    # Assuming quiz_badge_names is defined somewhere
    quiz_badge_names = [quiz_badge_names]

    # Convert badge names to URLs based on stored data
    quiz_badges = [{'name': badge_name, 'url': badge_data.get(badge_name, '')} for badge_name in quiz_badge_names]

    # Check if there are two past submissions
    if len(past_submissions_list) == 2:
        # Extract details of the latest and second latest submissions
        latest_submission = past_submissions_list[0]
        second_latest_submission = past_submissions_list[1]

        # Extracting click counts from the latest submission
        latest_add_extra_time_clicks = latest_submission.get('add_extra_time clicks', 0)
        latest_use_hint_clicks = latest_submission.get('use_hint_clicks', 0)
        latest_show_answer_clicks = latest_submission.get('show_answer_clicks', 0)

        # Extracting click counts from the second latest submission
        second_latest_add_extra_time_clicks = second_latest_submission.get('add_extra_time clicks', 0)
        second_latest_use_hint_clicks = second_latest_submission.get('use_hint_clicks', 0)
        second_latest_show_answer_clicks = second_latest_submission.get('show_answer_clicks', 0)

        # Compare the counts
        if (
            latest_add_extra_time_clicks > second_latest_add_extra_time_clicks or
            latest_use_hint_clicks > second_latest_use_hint_clicks or
            latest_show_answer_clicks > second_latest_show_answer_clicks
        ):
            message = "Why are you using these options too much? Think, in the last tests, you used them very less."
        else:
            message = "You are improving!"

        return render_template(
            'quiz_result_horror.html',
            course_name=course_name,
            quiz_name=quiz_name,
            result='horror',
            total_marks=total_marks,
            correct_ratio=correct_ratio,
            incorrect_ratio=incorrect_ratio,
            message=message,
            quiz_badges=quiz_badges
        )

    else:
        # Handle the case where there are not enough past submissions
        message = "Insufficient data for comparison."
        return render_template(
            'quiz_result_horror.html',
            course_name=course_name,
            quiz_name=quiz_name,
            result='nature',
            total_marks=total_marks,
            correct_ratio=correct_ratio,
            incorrect_ratio=incorrect_ratio,
            message=message,
            quiz_badges=quiz_badges
        )

@app.route('/quiz_result_nature/<course_name>/<quiz_name>/<total_marks>/<correct_ratio>/<incorrect_ratio>', methods=['GET'])
def quiz_result_nature(course_name, quiz_name, total_marks, correct_ratio, incorrect_ratio):
    user_email = session.get('email') or session.get('student_email')
    students_collection = db['students']
    quiz_collection = db['quiz']

    # Fetch details of the student's last two submissions for any quiz
    past_submissions = students_collection.find(
        {
            'email': user_email
        }
    ).sort('_id', -1).limit(2)
    # Convert the cursor to a list
    past_submissions_list = list(past_submissions)

    # Fetching quiz information from the quiz collection
    quiz_info = quiz_collection.find_one({'course_name': course_name, 'quiz_name': quiz_name})
    quiz_badge_names = quiz_info.get('badges', []) if quiz_info and 'badges' in quiz_info else []

    # Mapping of badge names to URLs based on stored data
    badge_data = {
        'pro': 'https://images.squarespace-cdn.com/content/v1/5ce4e383c91a190001537163/1653365043041-9SBNP4GHPLA1JXFSBKT7/Owl+5054+v6+Green+-+Black+-+600x600.gif',
        'intermediate': 'https://i.pinimg.com/originals/83/0e/f7/830ef72582287cfb5c7fbe61a24dbc36.gif',
        'beginner': 'https://cdn.dribbble.com/users/3278261/screenshots/6747984/ezgif.com-video-to-gif__11_.gif',
        # Add more mappings as needed
    }

    # Assuming quiz_badge_names is defined somewhere
    quiz_badge_names = [quiz_badge_names]

    # Convert badge names to URLs based on stored data
    quiz_badges = [{'name': badge_name, 'url': badge_data.get(badge_name, '')} for badge_name in quiz_badge_names]

    # Check if there are two past submissions
    if len(past_submissions_list) == 2:
        # Extract details of the latest and second latest submissions
        latest_submission = past_submissions_list[0]
        second_latest_submission = past_submissions_list[1]

        # Extracting click counts from the latest submission
        latest_add_extra_time_clicks = latest_submission.get('add_extra_time clicks', 0)
        latest_use_hint_clicks = latest_submission.get('use_hint_clicks', 0)
        latest_show_answer_clicks = latest_submission.get('show_answer_clicks', 0)

        # Extracting click counts from the second latest submission
        second_latest_add_extra_time_clicks = second_latest_submission.get('add_extra_time clicks', 0)
        second_latest_use_hint_clicks = second_latest_submission.get('use_hint_clicks', 0)
        second_latest_show_answer_clicks = second_latest_submission.get('show_answer_clicks', 0)

        # Compare the counts
        if (
            latest_add_extra_time_clicks > second_latest_add_extra_time_clicks or
            latest_use_hint_clicks > second_latest_use_hint_clicks or
            latest_show_answer_clicks > second_latest_show_answer_clicks
        ):
            message = "Why are you using these options too much? Think, in the last tests, you used them very less."
        else:
            message = "You are improving!"

        return render_template(
            'quiz_result_nature.html',
            course_name=course_name,
            quiz_name=quiz_name,
            result='nature',
            total_marks=total_marks,
            correct_ratio=correct_ratio,
            incorrect_ratio=incorrect_ratio,
            message=message,
            quiz_badges=quiz_badges
        )

    else:
        # Handle the case where there are not enough past submissions
        message = "Insufficient data for comparison."
        return render_template(
            'quiz_result_nature.html',
            course_name=course_name,
            quiz_name=quiz_name,
            result='nature',
            total_marks=total_marks,
            correct_ratio=correct_ratio,
            incorrect_ratio=incorrect_ratio,
            message=message,
            quiz_badges=quiz_badges
        )


@app.route('/quiz_result_fantasy/<course_name>/<quiz_name>/<total_marks>/<correct_ratio>/<incorrect_ratio>', methods=['GET'])
def quiz_result_fantasy(course_name, quiz_name, total_marks, correct_ratio, incorrect_ratio):
    user_email = session.get('email') or session.get('student_email')
    students_collection = db['students']
    quiz_collection = db['quiz']

    # Fetch details of the student's last two submissions for any quiz
    past_submissions = students_collection.find(
        {
            'email': user_email
        }
    ).sort('_id', -1).limit(2)
    # Convert the cursor to a list
    past_submissions_list = list(past_submissions)

    # Fetching quiz information from the quiz collection
    quiz_info = quiz_collection.find_one({'course_name': course_name, 'quiz_name': quiz_name})
    quiz_badge_names = quiz_info.get('badges', []) if quiz_info and 'badges' in quiz_info else []

    # Mapping of badge names to URLs based on stored data
    badge_data = {
        'pro': 'https://images.squarespace-cdn.com/content/v1/5ce4e383c91a190001537163/1653365043041-9SBNP4GHPLA1JXFSBKT7/Owl+5054+v6+Green+-+Black+-+600x600.gif',
        'intermediate': 'https://i.pinimg.com/originals/83/0e/f7/830ef72582287cfb5c7fbe61a24dbc36.gif',
        'beginner': 'https://cdn.dribbble.com/users/3278261/screenshots/6747984/ezgif.com-video-to-gif__11_.gif',
        # Add more mappings as needed
    }

    # Assuming quiz_badge_names is defined somewhere
    quiz_badge_names = [quiz_badge_names]

    # Convert badge names to URLs based on stored data
    quiz_badges = [{'name': badge_name, 'url': badge_data.get(badge_name, '')} for badge_name in quiz_badge_names]

    # Check if there are two past submissions
    if len(past_submissions_list) == 2:
        # Extract details of the latest and second latest submissions
        latest_submission = past_submissions_list[0]
        second_latest_submission = past_submissions_list[1]

        # Extracting click counts from the latest submission
        latest_add_extra_time_clicks = latest_submission.get('add_extra_time clicks', 0)
        latest_use_hint_clicks = latest_submission.get('use_hint_clicks', 0)
        latest_show_answer_clicks = latest_submission.get('show_answer_clicks', 0)

        # Extracting click counts from the second latest submission
        second_latest_add_extra_time_clicks = second_latest_submission.get('add_extra_time clicks', 0)
        second_latest_use_hint_clicks = second_latest_submission.get('use_hint_clicks', 0)
        second_latest_show_answer_clicks = second_latest_submission.get('show_answer_clicks', 0)

        # Compare the counts
        if (
            latest_add_extra_time_clicks > second_latest_add_extra_time_clicks or
            latest_use_hint_clicks > second_latest_use_hint_clicks or
            latest_show_answer_clicks > second_latest_show_answer_clicks
        ):
            message = "Why are you using these options too much? Think, in the last tests, you used them very less."
        else:
            message = "You are improving!"

        return render_template(
            'quiz_result_fantasy.html',
            course_name=course_name,
            quiz_name=quiz_name,
            result='fantasy',
            total_marks=total_marks,
            correct_ratio=correct_ratio,
            incorrect_ratio=incorrect_ratio,
            message=message,
            quiz_badges=quiz_badges
        )

    else:
        # Handle the case where there are not enough past submissions
        message = "Insufficient data for comparison."
        return render_template(
            'quiz_result_fantasy.html',
            course_name=course_name,
            quiz_name=quiz_name,
            result='fantasy',
            total_marks=total_marks,
            correct_ratio=correct_ratio,
            incorrect_ratio=incorrect_ratio,
            message=message,
            quiz_badges=quiz_badges
        )


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

    recommendation_result = get_user_recommendation_result(user_email)

    assignment_collection = db['assignment']
    assignment = assignment_collection.find_one({
        'course_name': course_name,
        'quiz_name': quiz_name,
        'assignment_name': assignment_name
    })

    if assignment:
        # Fetch learning level from the learning collection
        learning_level_document = learning_collection.find_one({'email': user_email}, {'learning_level': 1, '_id': 0})
        learning_level = learning_level_document.get('learning_level') if learning_level_document else None

        questions = assignment.get('questions', [])
        filtered_questions = []

        # Filter questions based on learning level
        for question in questions:
            if (
                (learning_level == 'quick learner' and question['difficulty_level'] == 'hard') or
                (learning_level == 'average learner' and question['difficulty_level'] == 'medium') or
                (learning_level == 'slow learner' and question['difficulty_level'] == 'easy')
            ):
                filtered_questions.append(question)

        if recommendation_result == 'based on above we recommend you horror theme to nourish and to grow':
            # Check if there are questions for the specified learning level
            if filtered_questions:
                # Randomly select one question
                selected_questions = random.sample(filtered_questions, k=1)  # You can adjust 'k' based on your preference
                return render_template('fill_assignment_horror.html', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name, questions=selected_questions)
            else:
                return render_template('error.html', message='No questions found for the specified learning level.')
        elif recommendation_result == 'based on above we recommend you nature content theme to nourish and to grow':
            if filtered_questions:
                # Randomly select one question
                selected_questions = random.sample(filtered_questions, k=1)  # You can adjust 'k' based on your preference
                return render_template('fill_assignment_nature.html', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name, questions=selected_questions)
            else:
                return render_template('error.html', message='No questions found for the specified learning level.')
        elif recommendation_result == 'based on above we recommend you fantasy theme to nourish and to grow':
            if filtered_questions:
                # Randomly select one question
                selected_questions = random.sample(filtered_questions, k=1)  # You can adjust 'k' based on your preference
                return render_template('fill_assignment_fantasy.html', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name, questions=selected_questions)
            else:
                return render_template('error.html', message='No questions found for the specified learning level.')
        else:
            return render_template('error.html', message='Invalid recommendation result.')
    else:
        return render_template('assignment_not_found.html')
    
@app.route('/completed_assignment/<course_name>/<quiz_name>/<assignment_name>', methods=['POST'])
def completed_assignment(course_name, quiz_name, assignment_name):
    user_email = session.get('email') or session.get('student_email')
    students_collection = db['students']

    # Fetch the total marks of the user based on the quiz_name
    user_data = students_collection.find_one({
        'email': user_email,
        'course_name': course_name,
        'quiz_name': quiz_name
    })

    if user_data:
        total_marks = user_data.get('total_marks', 0)  # Assuming a default of 0 if not found
    else:
        total_marks = 0  # Set a default value if no user_data is found

    # Get the questions and user answers from the request form
    questions_and_answers = {}
    for key, value in request.form.items():
        if key.startswith('user_answer_'):
            question_id = key.replace('user_answer_', '')
            question = request.form.get(f'question_{question_id}')
            user_answer = value
            questions_and_answers[question_id] = {
                'question': question,
                'user_answer': user_answer
            }
    print("question",question)
    print('answer',user_answer)
    # Insert each question and user answer separately
    for question_id, data in questions_and_answers.items():
        students_collection.update_one(
            {
                'email': user_email,
                'course_name': course_name,
                'quiz_name': quiz_name,
            },
            {
                '$addToSet': {
                    f'assignments.{assignment_name}.questions_and_answers': {
                        'question': data['question'],
                        'user_answer': data['user_answer']
                    }
                }
            }
        )

    # Update information about the completed assignment in the students_collection
    students_collection.update_one(
        {
            'email': user_email,
            'course_name': course_name,
            'quiz_name': quiz_name,
        },
        {
            '$set': {
                f'assignments.{assignment_name}': {
                    'completed': True,
                    'total_marks': total_marks,
                    'question':question,
                    'user_answer':user_answer
                }
            }
        }
    )

    return redirect(url_for('completed_assignment_page', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name))

@app.route('/completed_assignment_page/<course_name>/<quiz_name>/<assignment_name>')
def completed_assignment_page(course_name, quiz_name, assignment_name):
    # You can pass any additional data to the template if needed
    return render_template('completed_assignment.html', course_name=course_name, quiz_name=quiz_name, assignment_name=assignment_name)


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

@app.route('/retry_nature/<course_name>/<quiz_name>')
def retry_nature(course_name, quiz_name):
    return render_template('retry_nature.html', course_name=course_name, quiz_name=quiz_name)

@app.route('/retry_nature/<course_name>/<quiz_name>')
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


collection2 = db.assignment
collection3 = db.students
collection4 = db.slow
collection5 = db.average
collection6 = db.quick
def get_unique_options(course_name):
    # Get unique quiz names and assignment names from the database
    unique_quiz_names = collection2.distinct('quiz_name', {'course_name': course_name})
    unique_assignments = collection2.distinct('assignment_name', {'course_name': course_name})
    return unique_quiz_names, unique_assignments

@app.route('/submission_details', methods=['GET', 'POST'])
def submission_details():
    unique_course_names = collection2.distinct('course_name')  # Replace with actual course names

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        quiz_name = request.form.get('quiz_name')
        assignment_name = request.form.get('assignment_name')

        # Query the database based on the selected quiz_name and assignment_name
        try:
            data = collection3.find({"quiz_name": quiz_name, "course_name": course_name})
        except Exception as e:
            # Handle the exception, log it, or return an error page
            return render_template('error.html', error=str(e))

        unique_quiz_names, unique_assignments = get_unique_options(course_name)

        return render_template('submission_details.html', data=data, unique_quiz_names=unique_quiz_names,
                               unique_assignments=unique_assignments, selected_course=course_name,
                               unique_course_names=unique_course_names, assignment_name=assignment_name)

    # On initial load, provide default values or handle as needed
    return render_template('submission_details.html', unique_quiz_names=[], unique_assignments=[],
                           selected_course=None, unique_course_names=unique_course_names, assignment_name=None)
    
@app.route('/save_values', methods=['POST'])
def save_values():
    data = request.json
    print('data',data)
    user_email = data['userEmail']
    assessment_mark = data['assessmentMark']
    task1 = data['task1']
    attendance = data['attendance']
    preparation = data['preparation']
    ontime = data['ontime']
    quiz = data['total_marks']
    quiz_name1 = data['quiz_name']
    course_name= data['course_name']
    
    print(data)
    ttpoint = assessment_mark + task1 + attendance + preparation + ontime + int(quiz)
    ttpoint = ttpoint * 5
    print('ttpoint',ttpoint)
    user_data = student_collection.find_one({'email': user_email})
    total_coins = user_data.get('total_coins', 0)
    

    # Update the document with the provided values
    if data['ll'] == "slow learner":
        collection4.insert_one({
            'user_email': user_email,
            'assessment_mark': assessment_mark,
            'task1': task1,
            'attendance': attendance,
            'preparation': preparation,
            'ontime': ontime,
            'total_point': ttpoint,
            'quiz_name': quiz_name1,                    
            'course_name': course_name

        })
        student_collection.update_one(
            {'email': user_email},
            {'$set': {'total_coins': total_coins + ttpoint}},
            upsert=True
        )
        print("slow learner is coming")

    if data['ll'] == "average learner":
        collection5.insert_one({ 
            'user_email': user_email,
            'assessment_mark': assessment_mark,
            'task1': task1,
            'attendance': attendance,
            'preparation': preparation,
            'ontime': ontime,
            'total_point': ttpoint,
            'quiz_name': quiz_name1,
            'course_name': course_name

        })
        student_collection.update_one(
            {'email': user_email},
            {'$set': {'total_coins': total_coins + ttpoint}},
            upsert=True
        )
        print("average learner has arrived bro")
    
    if data['ll'] == "quick learner":
        collection6.insert_one({
            'user_email': user_email,
            'assessment_mark': assessment_mark,
            'task1': task1,
            'attendance': attendance,
            'preparation': preparation,
            'ontime': ontime,
            'total_point': ttpoint,
            'quiz_name': quiz_name1,
            'course_name': course_name

        })
        student_collection.update_one(
            {'email': user_email},
            {'$set': {'total_coins': total_coins + ttpoint}},
            upsert=True
        )
        print("quick learner is introduced")

    return jsonify({'status': 'success'})


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
        course_name = request.form['courseName']
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
    return render_template('give_quiz.html', course_name=course_name)


@app.route('/completed')
def completed():
    return render_template('completed.html')

@app.route("/give_assignment/<course_name>", methods=["GET", "POST"])
def give_assignment(course_name):
    if request.method == "POST":
        assignment_name = request.form["assignmentName"]
        quiz_name = request.form["quizName"]
        
        # Initialize an empty list to store questions
        questions = []

        # Iterate over form keys to extract questions
        question_keys = [key for key in request.form.keys() if key.startswith("question_")]
        for key in question_keys:
            question_index = key.split("_")[-1]
            question = {
                "question": request.form[f"question_{question_index}"],
                "difficulty": request.form[f"difficulty_{question_index}"],
            }
            questions.append(question)

        # Create the assignment_data dictionary
        assignment_data = {
            "course_name": course_name,
            "assignment_name": assignment_name,
            "quiz_name": quiz_name,
            "questions": questions,
        }

        # Insert the assignment_data into the database
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
        quiz_name = request.form["quizName"]
        slow_learner_material = request.form.get("slowLearnerMaterial")
        topper_material = request.form.get("topperMaterial")
        average_learner_material = request.form.get("averageLearnerMaterial")
        material_data = {
                "course_name": course_name,
                "quiz_name": quiz_name,
                "slow_learner_material": slow_learner_material,
                "topper_material": topper_material,
                "average_learner_material": average_learner_material,
            }
        result = material_collection.insert_one(material_data)
        if result.inserted_id:
            print("Material inserted successfully!")
            return redirect(url_for("completed"))  # Check if "completed" is the correct route
        else:
            print("Error inserting material!")
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
    app.run(host='0.0.0.0',port=5001)
