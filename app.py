import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from analyzer import analyze_entries

app = Flask(__name__)
CORS(app)

# Initialize Firebase (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")  # Your JSON file
    firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route('/debug/users', methods=['GET'])
def list_all_users():
    """
    Shows ALL user IDs in your Firebase with their data counts
    """
    try:
        print("🔍 Scanning all users in Firebase...")
        
        # Get ALL documents from users collection
        users_ref = db.collection('users').list_documents()
        
        user_list = []
        
        for user_doc_ref in users_ref:
            user_id = user_doc_ref.id
            print(f"Found user: {user_id}")
            
            user_info = {
                'user_id': user_id,
                'has_journals': False,
                'has_echo': False,
                'journal_count': 0,
                'echo_count': 0,
                'user_echo_count': 0,  # Only user messages
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
                    print(f"  └─ Journals: {journal_count}")
            except Exception as e:
                print(f"  └─ Journal error: {e}")
            
            # Check echo messages
            try:
                echo_ref = db.collection('users').document(user_id).collection('echo_history')
                echo_docs = list(echo_ref.stream())
                
                total_echo = len(echo_docs)
                user_echo = sum(1 for doc in echo_docs if doc.to_dict().get('sender') == 'user')
                
                user_info['echo_count'] = total_echo
                user_info['user_echo_count'] = user_echo
                
                if total_echo > 0:
                    user_info['has_echo'] = True
                
                print(f"  └─ Echo messages: {total_echo} (user: {user_echo})")
            except Exception as e:
                print(f"  └─ Echo error: {e}")
            
            user_list.append(user_info)
        
        print(f"\n✅ Found {len(user_list)} total users")
        
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
    """
    Analyze ALL users in the database at once
    """
    try:
        print("🔍 Analyzing all users...")
        
        users_ref = db.collection('users').list_documents()
        
        results = []
        
        for user_doc_ref in users_ref:
            user_id = user_doc_ref.id
            print(f"\n📊 Analyzing: {user_id}")
            
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
                
                # Get echo messages
                echo_ref = db.collection('users').document(user_id).collection('echo_history')
                echo_docs = echo_ref.stream()
                
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
                
                # Analyze if data exists
                if all_entries:
                    analysis = analyze_entries(all_entries)
                    analysis['user_id'] = user_id
                    analysis['total_entries'] = len(all_entries)
                    results.append(analysis)
                    print(f"  ✅ {len(all_entries)} entries analyzed")
                else:
                    results.append({
                        'user_id': user_id,
                        'status': 'no_data',
                        'message': 'No entries found'
                    })
                    print(f"  ⚠️ No data to analyze")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)