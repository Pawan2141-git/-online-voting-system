from flask import request, jsonify, current_app
from flask_login import current_user
import json
import urllib.request
import urllib.parse
from . import chat_bp
from models import db, Election, Candidate, ChatLog

def call_gemini_api(prompt, api_key):
    """Call Google Gemini 1.5 API using standard urllib."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    system_instruction = (
        "You are MatDan AI, the official intelligent assistant for the MatDan Online Voting System. "
        "Provide accurate, polite, and helpful answers regarding voter registration, election schedules, "
        "candidate profiles, vote anonymity (SHA256 hashing), and platform security. "
        "Keep your responses concise, professional, and formatted in clear markdown."
    )
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_instruction}\n\nUser Question: {prompt}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 500
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            candidates_res = res_data.get('candidates', [])
            if candidates_res:
                parts = candidates_res[0].get('content', {}).get('parts', [])
                if parts:
                    return parts[0].get('text', '').strip()
    except Exception as e:
        current_app.logger.warning(f"Gemini API call failed: {e}")
        return None
    return None


def get_smart_fallback_response(user_msg):
    msg = user_msg.lower()
    
    # Check election query
    if any(k in msg for k in ['election', 'schedule', 'timing', 'active', 'vote now']):
        try:
            active_elections = Election.query.filter_by(status='active').all()
            if active_elections:
                titles = ", ".join([f"**{e.title}**" for e in active_elections])
                return f"🗳️ Currently active election(s): {titles}. Head over to your Voter Dashboard to cast your vote!"
            else:
                return "ℹ️ There are no active elections at this moment. Check your Voter Dashboard for upcoming schedule updates."
        except Exception:
            return "ℹ️ You can view active and upcoming elections on the Home page or Voter Dashboard."

    # Candidate query
    if any(k in msg for k in ['candidate', 'who is running', 'party', 'symbol', 'manifesto']):
        try:
            candidates = Candidate.query.limit(5).all()
            if candidates:
                cand_list = "\n".join([f"- **{c.name}** ({c.party})" for c in candidates])
                return f"📋 Here are some registered candidates:\n{cand_list}\n\nVisit the election page for full manifestos and profiles!"
        except Exception:
            return "📋 Candidate details and election manifestos are available on the election voting pages."

    # How to vote query
    if any(k in msg for k in ['how to vote', 'steps', 'process', 'guide']):
        return (
            "📌 **How to Vote on MatDan Portal:**\n"
            "1. **Register/Login**: Ensure you are logged in with your EPIC Voter ID.\n"
            "2. **Navigate**: Go to your **Voter Dashboard**.\n"
            "3. **Select Election**: Click **Vote Now** on an active election.\n"
            "4. **Choose Candidate**: Review candidates and select your preferred choice.\n"
            "5. **Confirm**: Review the confirmation popup and submit your vote securely."
        )

    # Security query
    if any(k in msg for k in ['secure', 'anonymous', 'privacy', 'double vote', 'hack']):
        return (
            "🔒 **Security & Anonymity Guarantee:**\n"
            "- **Vote Privacy**: Your vote is stored as a cryptographic SHA-256 hash. Nobody can link your identity to your cast vote.\n"
            "- **One Vote Limit**: The database enforces single-vote constraints (`unique_user_election_vote`). Double voting is impossible.\n"
            "- **Audit Logging**: All administrative actions are recorded in immutable audit logs."
        )

    # Default assistance
    return (
        "Hello! I am **MatDan AI Assistant**. 🤖\n\n"
        "I can help you with:\n"
        "- 🗳️ Checking active election status\n"
        "- 👤 Finding candidate details & party symbols\n"
        "- 📝 Voting eligibility (18+ requirement & EPIC registration)\n"
        "- 🔒 Security, vote privacy & cryptographic hashing\n\n"
        "How can I assist you today?"
    )


@chat_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """Endpoint for AI Chatbot Assistant interactions with rate limiting and logging."""
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message content cannot be empty.'}), 400

    api_key = current_app.config.get('GEMINI_API_KEY', '')
    bot_response = None

    if api_key:
        bot_response = call_gemini_api(user_message, api_key)

    if not bot_response:
        bot_response = get_smart_fallback_response(user_message)

    # Log chat if LOG_CHAT is enabled
    if current_app.config.get('LOG_CHAT', True):
        try:
            uid = current_user.id if current_user and current_user.is_authenticated else None
            ip = request.remote_addr or '127.0.0.1'
            log = ChatLog(user_id=uid, user_message=user_message, bot_response=bot_response, ip_address=ip)
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to log chat interaction: {e}")

    return jsonify({
        'status': 'success',
        'message': bot_response
    })
