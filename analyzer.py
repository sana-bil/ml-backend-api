import pickle
import re
from datetime import datetime, timedelta
import numpy as np

# Load models (Ensure these files are in your 'models' folder!)
try:
    with open('models/svm_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('models/vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
except Exception as e:
    print(f"⚠️ Model Warning: {e}. Ensure models/ folder is correct.")

# Keywords for mental health detection
DEPRESSION_KEYWORDS = ['sad', 'depressed', 'hopeless', 'worthless', 'empty', 'tired', 'exhausted', 'sleep', 'insomnia', 'suicide', 'death', 'end it', 'no point', 'give up', 'meaningless', 'numb', 'alone', 'isolated', 'crying', 'tears', 'hurt', 'pain', 'broken']
ANXIETY_KEYWORDS = ['anxious', 'anxiety', 'worry', 'worried', 'nervous', 'panic', 'fear', 'scared', 'afraid', 'stress', 'stressed', 'overwhelmed', 'restless', 'tense', 'racing', 'cant breathe', 'heart racing']
SUICIDAL_KEYWORDS = ['kill myself', 'end it all', 'suicide', 'want to die', 'better off dead', 'no reason to live', 'end my life', 'hang myself', 'overdose', 'jump off']

def preprocess_text(text):
    """Clean text for model input"""
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    return ' '.join(text.split())

def get_sentiment(text):
    """Get sentiment: 0=negative, 1=positive using your SVM"""
    clean = preprocess_text(text)
    if not clean: return 1
    try:
        vec = vectorizer.transform([clean])
        return model.predict(vec)[0]
    except:
        return 0 # Default to negative if model fails to be safe

def count_keywords(text, keywords):
    return sum(1 for kw in keywords if kw in text.lower())

def analyze_entries(entries):
    if not entries:
        return {'depression_level': 'none', 'anxiety_level': 'none', 'risk_level': 'low', 'insights': ['Not enough data']}

    # CRASH FIX: Use current date for items like 'Chat/Echo' that don't have a real YYYY-MM-DD
    today = datetime.now().date()
    two_weeks_ago = today - timedelta(days=14)
    daily_analysis = {}

    for entry in entries:
        date_str = entry.get('date', 'Chat/Echo')
        text = entry.get('text', '')
        
        # --- THE CRITICAL FIX ---
        # If it's an Echo/Chat or missing a date, we treat it as "Today"
        try:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            entry_date = today # Treat Echo history as current data
            date_str = str(today) 

        # Skip if older than 2 weeks (DSM-V window)
        if entry_date < two_weeks_ago:
            continue
        
        if date_str not in daily_analysis:
            daily_analysis[date_str] = {'sentiments': [], 'dep_keywords': 0, 'anx_keywords': 0, 'sui_keywords': 0}
        
        daily_analysis[date_str]['sentiments'].append(get_sentiment(text))
        daily_analysis[date_str]['dep_keywords'] += count_keywords(text, DEPRESSION_KEYWORDS)
        daily_analysis[date_str]['anx_keywords'] += count_keywords(text, ANXIETY_KEYWORDS)
        daily_analysis[date_str]['sui_keywords'] += count_keywords(text, SUICIDAL_KEYWORDS)

    # Calculate metrics
    negative_days, anxiety_days, suicidal_days = 0, 0, 0
    total_dep_score, total_anx_score = 0, 0
    
    for date, data in daily_analysis.items():
        avg_sent = np.mean(data['sentiments']) if data['sentiments'] else 1
        if avg_sent < 0.5 or data['dep_keywords'] >= 3:
            negative_days += 1
            total_dep_score += data['dep_keywords']
        if data['anx_keywords'] >= 2:
            anxiety_days += 1
            total_anx_score += data['anx_keywords']
        if data['sui_keywords'] > 0:
            suicidal_days += 1

    # Classification logic (Your Original Logic)
    dep_lvl = 'none'
    if suicidal_days >= 2 or (negative_days >= 10 and total_dep_score >= 15): dep_lvl = 'severe'
    elif negative_days >= 7 or total_dep_score >= 10: dep_lvl = 'moderate'
    elif negative_days >= 3: dep_lvl = 'mild'

    anx_lvl = 'none'
    if anxiety_days >= 10 or total_anx_score >= 20: anx_lvl = 'severe'
    elif anxiety_days >= 7 or total_anx_score >= 12: anx_lvl = 'moderate'
    elif anxiety_days >= 3: anx_lvl = 'mild'

    risk = 'low'
    if suicidal_days > 0: risk = 'critical'
    elif dep_lvl == 'severe' or anx_lvl == 'severe': risk = 'high'
    elif dep_lvl == 'moderate' or anx_lvl == 'moderate': risk = 'medium'

    return {
        'status': 'success',
        'depression_level': dep_lvl,
        'anxiety_level': anx_lvl,
        'risk_level': risk,
        'negative_days': negative_days,
        'total_days_analyzed': len(daily_analysis),
        'crisis_detected': suicidal_days > 0
    }