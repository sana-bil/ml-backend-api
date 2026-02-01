import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from analyzer import analyze_entries

app = Flask(__name__)
CORS(app)

# Get port from environment (Render sets this automatically)
port = int(os.environ.get('PORT', 5000))

# Firebase initialization
secret_path = "/etc/secrets/serviceAccountKey.json" if os.path.exists("/etc/secrets/serviceAccountKey.json") else "serviceAccountKey.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(secret_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ===== ROOT ENDPOINT (REQUIRED FOR RENDER HEALTH CHECK) =====
@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Mental Health ML API is running! 🧠',
        'endpoints': {
            '/analyze/<user_id>': 'Analyze user mental health',
            '/debug/users': 'List all users',
            '/debug/analyze-all': 'Analyze all users',
            '/health': 'Check API status'
        }
    }), 200

@app.route('/health', methods=['GET'])
def health():
    """Another health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200

# ===== MAIN ANALYSIS ENDPOINT =====
@app.route('/analyze/<user_id>', methods=['GET'])
def analyze_user(user_id):
    """Analyze all journals + echo chats for a user"""
    try:
        print(f"🔍 Analyzing user: {user_id}")
        
        all_entries = []

        # Get journals
        try:
            logs_ref = db.collection('users').document(user_id).collection('data').document('logs')
            logs_doc = logs_ref.get()
            
            if logs_doc.exists:
                logs_data = logs_doc.to_dict()
                print(f"📔 Found journal data for {len(logs_data)} dates")
                
                for date_key, day_content in logs_data.items():
                    if not isinstance(day_content, dict):
                        continue
                    
                    journals = day_content.get('journals', [])
                    
                    for journal in journals:
                        if isinstance(journal, dict):
                            text = journal.get('text', '')
                            if text.strip():
                                all_entries.append({
                                    'text': text.strip(),
                                    'date': date_key,
                                    'source': 'journal'
                                })
        except Exception as e:
            print(f"⚠️ Journal fetch error: {e}")

        # Get echo messages
        try:
            echo_ref = db.collection('users').document(user_id).collection('echo_history')
            echo_docs = echo_ref.stream()
            
            echo_count = 0
            for doc in echo_docs:
                data = doc.to_dict()
                
                if data.get('sender') == 'user':
                    text = data.get('text', '')
                    if text.strip():
                        timestamp = data.get('timestamp')
                        if timestamp:
                            try:
                                date_str = timestamp.strftime('%Y-%m-%d')
                            except:
                                date_str = 'Chat/Echo'
                        else:
                            date_str = 'Chat/Echo'
                        
                        all_entries.append({
                            'text': text.strip(),
                            'date': date_str,
                            'source': 'echo'
                        })
                        echo_count += 1
            
            print(f"💬 Found {echo_count} Echo messages")
        except Exception as e:
            print(f"⚠️ Echo fetch error: {e}")

        # Check if we have data
        if not all_entries:
            return jsonify({
                'status': 'no_data',
                'message': 'No journal entries or chat messages found',
                'user_id': user_id
            }), 200

        print(f"📊 Total entries to analyze: {len(all_entries)}")

        # Run analysis
        results = analyze_entries(all_entries)
        
        results['user_id'] = user_id
        results['total_entries'] = len(all_entries)
        results['analyzed_at'] = datetime.now().isoformat()

        # Save results to Firebase
        try:
            db.collection('users').document(user_id).collection('analysis_results').add({
                **results,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            print("✅ Results saved to Firebase")
        except Exception as e:
            print(f"⚠️ Save error: {e}")

        return jsonify(results), 200

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Analysis failed'
        }), 500

# ===== DEBUG ENDPOINTS =====
@app.route('/debug/users', methods=['GET'])
def list_all_users():
    """Shows ALL user IDs with their data counts"""
    try:
        print("🔍 Scanning all users...")
        
        users_ref = db.collection('users').list_documents()
        user_list = []
        
        for user_doc_ref in users_ref:
            user_id = user_doc_ref.id
            
            user_info = {
                'user_id': user_id,
                'has_journals': False,
                'has_echo': False,
                'journal_count': 0,
                'echo_count': 0,
                'user_echo_count': 0,
                'dates_with_data': []
            }
            
            # Check journals
            try:
                logs_ref = db.collection('users').document(user_id).collection('data').document('logs')
                logs_doc = logs_ref.get()
                
                if logs_doc.exists:
                    user_info['has_journals'] = True
                    logs_data = logs_doc.to_dict()
                    
                    journal_count = 0
                    for date_key, day_content in logs_data.items():
                        if isinstance(day_content, dict):
                            journals = day_content.get('journals', [])
                            if journals:
                                journal_count += len(journals)
                                user_info['dates_with_data'].append(date_key)
                    
                    user_info['journal_count'] = journal_count
            except Exception as e:
                print(f"Journal error: {e}")
            
            # Check echo
            try:
                echo_ref = db.collection('users').document(user_id).collection('echo_history')
                echo_docs = list(echo_ref.stream())
                
                total_echo = len(echo_docs)
                user_echo = sum(1 for doc in echo_docs if doc.to_dict().get('sender') == 'user')
                
                user_info['echo_count'] = total_echo
                user_info['user_echo_count'] = user_echo
                
                if total_echo > 0:
                    user_info['has_echo'] = True
            except Exception as e:
                print(f"Echo error: {e}")
            
            user_list.append(user_info)
        
        return jsonify({
            'total_users': len(user_list),
            'users': user_list,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/debug/analyze-all', methods=['GET'])
def analyze_all_users():
    """Analyze ALL users at once"""
    try:
        users_ref = db.collection('users').list_documents()
        results = []
        
        for user_doc_ref in users_ref:
            user_id = user_doc_ref.id
            
            try:
                all_entries = []
                
                # Get journals
                logs_ref = db.collection('users').document(user_id).collection('data').document('logs')
                logs_doc = logs_ref.get()
                
                if logs_doc.exists:
                    logs_data = logs_doc.to_dict()
                    
                    for date_key, day_content in logs_data.items():
                        if isinstance(day_content, dict):
                            journals = day_content.get('journals', [])
                            
                            for journal in journals:
                                if isinstance(journal, dict):
                                    text = journal.get('text', '')
                                    if text.strip():
                                        all_entries.append({
                                            'text': text.strip(),
                                            'date': date_key,
                                            'source': 'journal'
                                        })
                
                # Get echo
                echo_ref = db.collection('users').document(user_id).collection('echo_history')
                echo_docs = echo_ref.stream()
                
                for doc in echo_docs:
                    data = doc.to_dict()
                    
                    if data.get('sender') == 'user':
                        text = data.get('text', '')
                        if text.strip():
                            timestamp = data.get('timestamp')
                            date_str = timestamp.strftime('%Y-%m-%d') if timestamp else 'Chat/Echo'
                            
                            all_entries.append({
                                'text': text.strip(),
                                'date': date_str,
                                'source': 'echo'
                            })
                
                # Analyze
                if all_entries:
                    analysis = analyze_entries(all_entries)
                    analysis['user_id'] = user_id
                    analysis['total_entries'] = len(all_entries)
                    results.append(analysis)
                else:
                    results.append({
                        'user_id': user_id,
                        'status': 'no_data',
                        'message': 'No entries found'
                    })
                    
            except Exception as e:
                results.append({
                    'user_id': user_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'total_users_analyzed': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ===== RUN APP =====
if __name__ == '__main__':
    # Don't set debug=True in production
    app.run(host='0.0.0.0', port=port, debug=False)