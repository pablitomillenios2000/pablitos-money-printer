from flask import Flask, request, jsonify
from pywebpush import webpush, WebPushException
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)


with open('vapid_private_key.pem', 'r') as f:
    VAPID_PRIVATE_KEY = f.read()

with open('vapid_public_key.pem', 'r') as f:
    VAPID_PUBLIC_KEY = f.read()

VAPID_CLAIMS = {
    "sub": "mailto:youremail@example.com"
}

@app.route('/vapidPublicKey')
def vapid_public_key():
    return VAPID_PUBLIC_KEY

@app.route('/sendNotification', methods=['POST'])
def send_notification():
    subscription_info = request.json.get('subscription')
    payload = request.json.get('payload', {})

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
        return jsonify({'success': True})
    except WebPushException as ex:
        return jsonify({'success': False, 'error': str(ex)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5080)
