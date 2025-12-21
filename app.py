import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

# Database Connection (Port 6543 for Transaction Mode)
DB_URI = os.getenv("DB_URI")

def get_db_connection():
    return psycopg2.connect(DB_URI, sslmode='require', cursor_factory=RealDictCursor)

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM channels ORDER BY id DESC")
    channels = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', channels=channels)

@app.route('/channel/add', methods=['GET', 'POST'])
def add_channel():
    if request.method == 'POST':
        data = request.form
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO channels (name, rss_url, telegram_chat_id, bot_token, test_chat_id, 
                                  var_1_name, var_1_css, var_2_name, var_2_css, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (data['name'], data['rss_url'], data['telegram_chat_id'], data['bot_token'], 
              data.get('test_chat_id'), data['var_1_name'], data['var_1_css'], 
              data['var_2_name'], data['var_2_css'], True))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    return render_template('channel.html', channel=None)

@app.route('/channel/edit/<int:id>', methods=['GET', 'POST'])
def edit_channel(id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        data = request.form
        cur.execute("""
            UPDATE channels SET 
                name=%s, rss_url=%s, telegram_chat_id=%s, bot_token=%s, test_chat_id=%s,
                var_1_name=%s, var_1_css=%s, var_2_name=%s, var_2_css=%s, is_active=%s
            WHERE id=%s
        """, (data['name'], data['rss_url'], data['telegram_chat_id'], data['bot_token'], 
              data.get('test_chat_id'), data['var_1_name'], data['var_1_css'], 
              data['var_2_name'], data['var_2_css'], 'is_active' in data, id))
        conn.commit()
        return redirect(url_for('index'))
    
    cur.execute("SELECT * FROM channels WHERE id = %s", (id,))
    channel = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('channel.html', channel=channel)

# --- N8N PROXY ROUTES ---

@app.route('/proxy/magic', methods=['POST'])
def proxy_magic():
    webhook_url = os.getenv("N8N_MAGIC_WEBHOOK_URL")
    if not webhook_url:
        return jsonify({"error": "N8N_MAGIC_WEBHOOK_URL not set"}), 500
    
    try:
        # Forward the request to n8n
        response = requests.post(webhook_url, json=request.json, timeout=30)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/proxy/test', methods=['POST'])
def proxy_test():
    webhook_url = os.getenv("N8N_TEST_WEBHOOK_URL")
    if not webhook_url:
        return jsonify({"error": "N8N_TEST_WEBHOOK_URL not set"}), 500
    
    try:
        response = requests.post(webhook_url, json=request.json, timeout=30)
        return jsonify({"status": "sent", "n8n_response": response.status_code})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
