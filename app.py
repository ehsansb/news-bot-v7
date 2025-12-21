from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json

app = Flask(__name__)

# تنظیمات امنیتی و دیتابیس
app.secret_key = os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_LONG_RANDOM_STRING")
DB_URI = os.getenv("DB_URI")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

def get_db():
    return psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            session.permanent = True 
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect('/')
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM channels ORDER BY created_at DESC")
        channels = cur.fetchall()
        
        # آمار پست‌های امروز
        for c in channels:
            cur.execute("SELECT COUNT(*) as cnt FROM news_queue WHERE channel_ref_id = %s AND created_at > NOW() - INTERVAL '1 day'", (c['id'],))
            c['daily_usage_count'] = cur.fetchone()['cnt']
            
        conn.close()
        return render_template('dashboard.html', channels=channels, msg=request.args.get('msg'))
    except Exception as e:
        return f"Database Error: {e}"

@app.route('/add_channel', methods=['POST'])
def add_channel():
    if not session.get('logged_in'): return redirect('/')
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO channels (name, telegram_token, channel_id) VALUES (%s, %s, %s)",
                    (request.form['name'], request.form['token'], request.form['channel_id']))
        conn.commit()
        conn.close()
    except Exception as e:
        return f"Error: {e}"
    return redirect('/dashboard')

@app.route('/channel/<uuid:id>')
def channel_manager(id):
    if not session.get('logged_in'): return redirect('/')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM channels WHERE id = %s", (str(id),))
    channel = cur.fetchone()
    conn.close()
    
    if not channel: return "Not Found"
    
    def ensure_json(data):
        if isinstance(data, str): return data
        return json.dumps(data or [])

    return render_template('channel.html', 
                           channel=channel, 
                           variables_json=json.dumps(channel.get('variables_config') or {}),
                           sources_json=ensure_json(channel.get('rss_config')),
                           crawlers_json=ensure_json(channel.get('crawler_config')))

@app.route('/update_channel/<uuid:id>', methods=['POST'])
def update_channel(id):
    if not session.get('logged_in'): return redirect('/')
    data = request.form
    try:
        conn = get_db()
        cur = conn.cursor()
        
        active = True if data.get('channel_active') == 'true' or data.get('channel_active') == 'on' else False
        
        # ذخیره تمام اطلاعات شامل آیدی تست و توکن‌ها
        cur.execute("""
            UPDATE channels SET 
            name=%s, interval=%s, active=%s, button_text=%s,
            telegram_token=%s, channel_id=%s, test_chat_id=%s,
            content_template=%s, variables_config=%s, rss_config=%s, crawler_config=%s
            WHERE id=%s
        """, (
            data['name'], data['interval'], active, data['button_text'],
            data['telegram_token'], data['channel_id'], data['test_chat_id'],
            data['content_template'],
            data['variables_config'], data['rss_config'], data['crawler_config'],
            str(id)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        return f"Error saving: {e}"
        
    return redirect(f'/channel/{id}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
