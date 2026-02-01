import pandas as pd
import numpy as np
import re
import pickle
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, classification_report
import nltk
from nltk.corpus import stopwords

# Download stopwords
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# ===== STEP 1: LOAD DATA =====
print("📂 Loading dataset...")

# Dataset has 6 columns: [target, id, date, flag, user, text]
# target: 0 = negative, 4 = positive
columns = ['target', 'id', 'date', 'flag', 'user', 'text']

df = pd.read_csv('C:\\Users\\Home\\Documents\\Projects\\liberate-me\\Dataset\\training.1600000.processed.noemoticon.csv', 
                 encoding='latin-1', 
                 names=columns)

print(f"✅ Loaded {len(df)} tweets")

# Take a sample for faster training (optional - remove for full training)
# df = df.sample(n=100000, random_state=42)  # Use 100k for testing
# For production: use all 1.6M

# ===== STEP 2: PREPROCESS TEXT =====
print("🧹 Cleaning text...")

def preprocess_text(text):
    """Clean tweet text"""
    # Lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    
    # Remove mentions and hashtags
    text = re.sub(r'@\w+|#\w+', '', text)
    
    # Remove special characters and numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Remove stopwords
    text = ' '.join([word for word in text.split() if word not in stop_words])
    
    return text

df['clean_text'] = df['text'].apply(preprocess_text)

# Remove empty tweets
df = df[df['clean_text'].str.len() > 0]

print(f"✅ Cleaned {len(df)} tweets")

# ===== STEP 3: PREPARE DATA =====
print("🔢 Preparing data...")

# Convert target: 0 stays 0 (negative), 4 becomes 1 (positive)
df['sentiment'] = df['target'].apply(lambda x: 0 if x == 0 else 1)

X = df['clean_text']
y = df['sentiment']

# Split data: 80% train, 20% test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"📊 Training samples: {len(X_train)}")
print(f"📊 Testing samples: {len(X_test)}")

# ===== STEP 4: VECTORIZE TEXT =====


vectorizer = TfidfVectorizer(
    max_features=5000,  # Use top 5000 words
    ngram_range=(1, 2),  # Use unigrams and bigrams
    min_df=5,  # Ignore words that appear in less than 5 documents
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

print(f"✅ Vocabulary size: {len(vectorizer.vocabulary_)}")

# ===== STEP 5: TRAIN SVM MODEL =====
print("🧠 Training SVM model (this will take several minutes)...")

model = LinearSVC(
    random_state=42,
    max_iter=1000,
    C=1.0
)

model.fit(X_train_vec, y_train)

print("✅ Model trained!")

# ===== STEP 6: EVALUATE MODEL =====
print("📈 Evaluating model...")

y_pred = model.predict(X_test_vec)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n🎯 Accuracy: {accuracy * 100:.2f}%")
print("\n📊 Classification Report:")
print(classification_report(y_test, y_pred, target_names=['Negative', 'Positive']))

# ===== STEP 7: SAVE MODEL =====
print("💾 Saving model...")

# Create models directory
import os
os.makedirs('models', exist_ok=True)

# Save model
with open('models/svm_model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Save vectorizer
with open('models/vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

print("✅ Model saved to models/svm_model.pkl")
print("✅ Vectorizer saved to models/vectorizer.pkl")

# ===== STEP 8: TEST MODEL =====
print("\n🧪 Testing with sample texts...")

test_texts = [
    "I'm feeling really happy today!",
    "I hate everything, life is terrible",
    "Just another normal day",
    "I feel so worthless and alone",
    "Everything is amazing, best day ever!"
]

for text in test_texts:
    clean = preprocess_text(text)
    vec = vectorizer.transform([clean])
    pred = model.predict(vec)[0]
    sentiment = "POSITIVE" if pred == 1 else "NEGATIVE"
    print(f"Text: {text}")
    print(f"Prediction: {sentiment}\n")

print("TRAINING COMPLETE!")