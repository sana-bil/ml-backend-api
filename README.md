🧠 Liberate Me: ML Sentiment & Psychiatric Analysis ModuleThis module serves as the "brain" of the Liberate Me platform.
It uses a hybrid approach of Machine Learning (SVM) and Lexicon-based Keyword Extraction to monitor user mental health patterns over a rolling 14-day window, strictly aligned with DSM-V diagnostic criteria.

🚀 Key FeaturesHybrid Analysis Engine: 
Combines a Support Vector Machine (SVM) model (trained on 1.6M data points) with clinical keyword detection.
DSM-V Alignment: Implements the "2-week symptom window" required for clinical depression and anxiety screening.
Multi-Source Data Aggregation: Pulls and analyzes data from both private Journal entries and Echo AI (Chatbot) history.Risk Stratification: 
Automatically flags "Critical" risk levels if suicidal ideation is detected in any text entry.

🛠️ System Architecture
The backend is built using Flask and integrates with Firebase Firestore.
1. Sentiment Analysis (SVM)Uses a pre-trained SVM model and a TF-IDF Vectorizer to classify the baseline mood of every entry as Positive (1) or Negative (0).
2. Clinical Logic (The Analyzer)The analyzer.py processes raw text into psychiatric insights:
Depression Detection: Scans for passive states (e.g., hopeless, worthless, insomnia).
Anxiety Detection: Scans for active distress and physical symptoms (e.g., panic, racing heart, overwhelmed).
Temporal Tracking: Aggregates scores day-by-day to see if symptoms persist for "most days" out of the 14-day window.

📊 Psychiatric Classification Logic Level
Depression Criteria (14-day window)
Anxiety Criteria (14-day window)
SevereSuicidal ideation (2+ days) OR 10+ negative days10+ anxiety-heavy days OR score > 20Moderate7+ negative days OR keyword score > 107+ anxiety days OR score > 12Mild3+ negative days3+ anxiety days
🔌 API Endpoints
GET /debug/usersScans the entire Firebase database to provide an overview of all registered users and their data density.Returns: User IDs, Journal counts, and Echo Chat counts.
GET /debug/analyze-allRuns the full ML diagnostic suite on every user in the database.Returns: A list of objects containing depression_level, anxiety_level, risk_level, and crisis_detected flags for each UID.📦 Installation & SetupClone the module:Bashgit clone [your-repo-url]

cd ml-backend
Install Dependencies:Bashpip install -r requirements.txt
Authentication:Place your serviceAccountKey.json (Firebase Admin SDK) in the root folder. Note: This file is ignored by Git for security.
Run Locally:Bashpython app.py
