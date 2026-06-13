from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import uuid
import os
from datetime import datetime

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'visits.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id TEXT PRIMARY KEY,
                business_name TEXT NOT NULL,
                owner_name TEXT,
                area TEXT,
                business_type TEXT,
                pain_quote TEXT,
                pain_level INTEGER DEFAULT 0,
                interest TEXT,
                whatsapp TEXT,
                current_tool TEXT,
                notes TEXT,
                followed_up INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/visits', methods=['GET'])
def get_visits():
    filter_by = request.args.get('filter', 'all')
    with get_db() as conn:
        if filter_by == 'hot':
            rows = conn.execute('SELECT * FROM visits WHERE pain_level = 3 ORDER BY created_at DESC').fetchall()
        elif filter_by == 'followup':
            rows = conn.execute("SELECT * FROM visits WHERE interest IN ('yes','paying') ORDER BY created_at DESC").fetchall()
        elif filter_by == 'pending':
            rows = conn.execute('SELECT * FROM visits WHERE followed_up = 0 ORDER BY created_at DESC').fetchall()
        else:
            rows = conn.execute('SELECT * FROM visits ORDER BY created_at DESC').fetchall()
        return jsonify([dict(r) for r in rows])

@app.route('/api/visits', methods=['POST'])
def add_visit():
    data = request.json
    if not data.get('business_name'):
        return jsonify({'error': 'Business name is required'}), 400
    visit_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    with get_db() as conn:
        conn.execute('''
            INSERT INTO visits (id, business_name, owner_name, area, business_type,
                pain_quote, pain_level, interest, whatsapp, current_tool, notes, followed_up, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            visit_id,
            data.get('business_name',''),
            data.get('owner_name',''),
            data.get('area',''),
            data.get('business_type',''),
            data.get('pain_quote',''),
            data.get('pain_level', 0),
            data.get('interest',''),
            data.get('whatsapp',''),
            data.get('current_tool',''),
            data.get('notes',''),
            0,
            now
        ))
        conn.commit()
    return jsonify({'id': visit_id, 'created_at': now}), 201

@app.route('/api/visits/<visit_id>', methods=['DELETE'])
def delete_visit(visit_id):
    with get_db() as conn:
        conn.execute('DELETE FROM visits WHERE id = ?', (visit_id,))
        conn.commit()
    return jsonify({'deleted': True})

@app.route('/api/visits/<visit_id>/followup', methods=['PATCH'])
def toggle_followup(visit_id):
    with get_db() as conn:
        row = conn.execute('SELECT followed_up FROM visits WHERE id = ?', (visit_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        new_val = 0 if row['followed_up'] else 1
        conn.execute('UPDATE visits SET followed_up = ? WHERE id = ?', (new_val, visit_id))
        conn.commit()
    return jsonify({'followed_up': bool(new_val)})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) FROM visits').fetchone()[0]
        hot = conn.execute('SELECT COUNT(*) FROM visits WHERE pain_level = 3').fetchone()[0]
        warm = conn.execute('SELECT COUNT(*) FROM visits WHERE pain_level = 2').fetchone()[0]
        followup = conn.execute("SELECT COUNT(*) FROM visits WHERE interest IN ('yes','paying')").fetchone()[0]
        pending = conn.execute('SELECT COUNT(*) FROM visits WHERE followed_up = 0').fetchone()[0]

        type_rows = conn.execute('''
            SELECT business_type, COUNT(*) as cnt FROM visits
            WHERE business_type != '' GROUP BY business_type ORDER BY cnt DESC
        ''').fetchall()

        interest_rows = conn.execute('''
            SELECT interest, COUNT(*) as cnt FROM visits
            WHERE interest != '' GROUP BY interest ORDER BY cnt DESC
        ''').fetchall()

        pain_rows = conn.execute('''
            SELECT pain_level, COUNT(*) as cnt FROM visits
            WHERE pain_level > 0 GROUP BY pain_level ORDER BY pain_level DESC
        ''').fetchall()

    return jsonify({
        'total': total, 'hot': hot, 'warm': warm,
        'followup': followup, 'pending': pending,
        'by_type': [dict(r) for r in type_rows],
        'by_interest': [dict(r) for r in interest_rows],
        'by_pain': [dict(r) for r in pain_rows]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)