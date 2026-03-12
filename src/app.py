"""
TeamKahoot — Backend (Railway)
Flask + Flask-SocketIO + MySQL (PyMySQL)
"""

import os, random, time, json
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import pymysql
import pymysql.cursors
import bcrypt
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

# ── App ───────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'kahoot-secret-2024')

FRONTEND_URL = os.getenv('FRONTEND_URL', '*')
CORS(app, origins=[FRONTEND_URL, 'http://localhost:3000', 'http://127.0.0.1:3000'])
socketio = SocketIO(
    app,
    cors_allowed_origins=[FRONTEND_URL, 'http://localhost:3000', 'http://127.0.0.1:3000', '*'],
    async_mode='eventlet',
    logger=False,
    engineio_logger=False
)

# ── Database ──────────────────────────────────────────────────
def parse_db_url(url):
    """Parse DATABASE_URL into PyMySQL connect kwargs."""
    p = urlparse(url)
    return {
        'host':    p.hostname,
        'port':    p.port or 3306,
        'user':    p.username,
        'password': p.password,
        'database': p.path.lstrip('/'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
    }

def get_db():
    url = os.getenv('DATABASE_URL', '')
    kwargs = parse_db_url(url)
    return pymysql.connect(**kwargs)

def query(sql, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    result = None
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetchone:
                row = cur.fetchone()
                result = dict(row) if row else None
            if fetchall:
                result = [dict(r) for r in cur.fetchall()]
            if commit:
                conn.commit()
                # For INSERT — return lastrowid as {'id': ...}
                if result is None and cur.lastrowid:
                    result = {'id': cur.lastrowid}
    finally:
        conn.close()
    return result

def query_returning(sql, params, returning_sql, returning_params):
    """Execute INSERT then fetch the inserted row (MySQL has no RETURNING)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            last_id = cur.lastrowid
        with conn.cursor() as cur:
            cur.execute(returning_sql, (last_id,) if returning_params == 'lastrowid' else returning_params)
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

# ── In-memory game rooms ──────────────────────────────────────
rooms: dict = {}

# ── Helpers ──────────────────────────────────────────────────
CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

def make_code():
    while True:
        code = ''.join(random.choices(CHARS, k=6))
        if code not in rooms:
            return code

def get_questions(topic_id):
    rows = query(
        'SELECT * FROM questions WHERE topic_id=%s ORDER BY RAND() LIMIT 10',
        (topic_id,), fetchall=True
    ) or []
    for r in rows:
        if isinstance(r.get('answer_options'), str):
            r['answer_options'] = json.loads(r['answer_options'])
        # MySQL returns TINYINT for booleans — normalize
        if 'is_correct' in r:
            r['is_correct'] = bool(r['is_correct'])
    return rows

def room_pub(room):
    players = list(room['players'].values())
    return {
        'code':    room['code'],
        'topic':   room['topic'],
        'teamA':   [p for p in players if p['team'] == 'A'],
        'teamB':   [p for p in players if p['team'] == 'B'],
        'players': players,
        'state':   room['state'],
    }

def next_team(room):
    return 'A' if len(room['players']) % 2 == 0 else 'B'

# ═════════════════════════════════════════════════════════════
#  REST API
# ═════════════════════════════════════════════════════════════

@app.route('/api/health')
def health():
    return jsonify(status='ok')

@app.route('/api/register', methods=['POST'])
def register():
    d        = request.json or {}
    username = (d.get('username') or '').strip()
    email    = (d.get('email')    or '').strip().lower()
    password = d.get('password')  or ''

    if not username or not email or not password:
        return jsonify(error='Todos los campos son obligatorios'), 400
    if len(username) < 3:
        return jsonify(error='El nombre debe tener al menos 3 caracteres'), 400
    if len(password) < 6:
        return jsonify(error='La contrasena debe tener al menos 6 caracteres'), 400
    try:
        exists = query(
            'SELECT id FROM users WHERE email=%s OR username=%s',
            (email, username), fetchone=True
        )
        if exists:
            return jsonify(error='Email o nombre de usuario ya en uso'), 409

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        avatar  = random.randint(1, 8)

        user = query_returning(
            'INSERT INTO users (username, email, password_hash, avatar) VALUES (%s,%s,%s,%s)',
            (username, email, pw_hash, avatar),
            'SELECT id, username, email, avatar, games_played, total_score FROM users WHERE id=%s',
            'lastrowid'
        )
        return jsonify(success=True, user=user), 201
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/login', methods=['POST'])
def login():
    d        = request.json or {}
    email    = (d.get('email')    or '').strip().lower()
    password = d.get('password')  or ''
    if not email or not password:
        return jsonify(error='Email y contrasena requeridos'), 400
    try:
        user = query('SELECT * FROM users WHERE email=%s', (email,), fetchone=True)
        if not user:
            return jsonify(error='Usuario no encontrado'), 401
        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return jsonify(error='Contrasena incorrecta'), 401
        query('UPDATE users SET last_seen=NOW() WHERE id=%s', (user['id'],), commit=True)
        return jsonify(success=True, user={
            'id': user['id'], 'username': user['username'],
            'email': user['email'], 'avatar': user['avatar'],
            'games_played': user['games_played'], 'total_score': user['total_score'],
        })
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/topics')
def topics():
    try:
        rows = query('SELECT * FROM topics ORDER BY id', fetchall=True)
        return jsonify(rows)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/leaderboard')
def leaderboard():
    try:
        rows = query(
            'SELECT username,total_score,games_played,games_won FROM users ORDER BY total_score DESC LIMIT 10',
            fetchall=True
        )
        return jsonify(rows)
    except Exception as e:
        return jsonify(error=str(e)), 500

# ═════════════════════════════════════════════════════════════
#  SOCKET.IO EVENTS
# ═════════════════════════════════════════════════════════════

@socketio.on('create-room')
def on_create_room(data):
    topic_id  = data.get('topicId')
    host_name = (data.get('hostName') or 'Anfitrion').strip()
    user_id   = data.get('userId')

    topic = query('SELECT * FROM topics WHERE id=%s', (topic_id,), fetchone=True)
    if not topic:
        emit('error', {'msg': 'Tema no encontrado'}); return

    questions = get_questions(topic_id)
    if not questions:
        emit('error', {'msg': 'Sin preguntas para este tema'}); return

    code   = make_code()
    avatar = random.randint(1, 8)
    player = {
        'socketId': request.sid, 'userId': user_id,
        'username': host_name, 'team': 'A',
        'score': 0, 'streak': 0, 'avatar': avatar, 'isHost': True,
    }
    rooms[code] = {
        'code': code, 'topic': topic, 'questions': questions,
        'host_sid': request.sid, 'host_name': host_name,
        'players': {request.sid: player},
        'state': 'waiting',
        'current_idx': -1, 'current_q': None,
        'q_answers': {}, 'team_scores': {'A': 0, 'B': 0},
        'q_start_ms': None, 'timer_cancel': False,
    }
    join_room(code)
    emit('room-created', {
        'roomCode': code, 'topic': topic,
        'questionCount': len(questions),
        'player': player, 'room': room_pub(rooms[code]),
    })

@socketio.on('join-room')
def on_join_room(data):
    code     = (data.get('roomCode') or '').upper().strip()
    username = (data.get('username') or '').strip()
    user_id  = data.get('userId')

    if code not in rooms:
        emit('join-error', {'msg': 'Sala no encontrada. Verifica el codigo.'}); return
    room = rooms[code]
    if room['state'] != 'waiting':
        emit('join-error', {'msg': 'El juego ya comenzo.'}); return
    if not username:
        emit('join-error', {'msg': 'Necesitas un nombre.'}); return
    for p in room['players'].values():
        if p['username'].lower() == username.lower():
            emit('join-error', {'msg': 'Ese nombre ya esta en uso en esta sala.'}); return

    team   = next_team(room)
    player = {
        'socketId': request.sid, 'userId': user_id,
        'username': username, 'team': team,
        'score': 0, 'streak': 0, 'avatar': random.randint(1, 8), 'isHost': False,
    }
    room['players'][request.sid] = player
    join_room(code)
    pub = room_pub(room)
    emit('joined-room', {'player': player, 'room': pub})
    emit('player-joined', {'player': player, **pub}, to=code)

@socketio.on('start-game')
def on_start_game(data):
    code = data.get('roomCode')
    if code not in rooms: return
    room = rooms[code]
    if request.sid != room['host_sid']: return
    if len(room['players']) < 2:
        emit('error', {'msg': 'Necesitas al menos 2 jugadores.'}); return
    room['state']        = 'countdown'
    room['timer_cancel'] = False

    def run_cd():
        for n in range(3, 0, -1):
            socketio.emit('countdown-tick', {'countdown': n}, to=code)
            socketio.sleep(1)
            if rooms.get(code, {}).get('timer_cancel'): return
        rooms[code]['current_idx'] = 0
        send_question(code)

    socketio.start_background_task(run_cd)

@socketio.on('submit-answer')
def on_answer(data):
    code        = data.get('roomCode')
    question_id = data.get('questionId')
    ans_idx     = data.get('answerIndex')
    if code not in rooms: return
    room = rooms[code]
    if room['state'] != 'question': return
    player = room['players'].get(request.sid)
    if not player or request.sid in room['q_answers']: return
    q = room['current_q']
    if not q or q['id'] != question_id: return

    elapsed_s   = (time.time() * 1000 - room['q_start_ms']) / 1000
    is_correct  = (ans_idx == q['correct_answer'])
    speed_ratio = max(0.0, 1.0 - elapsed_s / q['time_limit'])
    base        = 200 if is_correct else 0
    speed_bonus = int(speed_ratio * 800) if is_correct else 0
    player['streak'] = player['streak'] + 1 if is_correct else 0
    streak_bonus = min((player['streak'] - 1) * 50, 200) if is_correct and player['streak'] > 1 else 0
    pts = base + speed_bonus + streak_bonus

    room['q_answers'][request.sid] = {'answerIndex': ans_idx, 'isCorrect': is_correct, 'points': pts}
    if is_correct:
        player['score']                     += pts
        room['team_scores'][player['team']] += pts

    emit('answer-result', {
        'isCorrect': is_correct, 'points': pts,
        'correctAnswer': q['correct_answer'], 'streak': player['streak'],
    })
    answered = len(room['q_answers'])
    total_p  = len(room['players'])
    socketio.emit('answer-count', {'answered': answered, 'total': total_p}, to=code)
    if answered >= total_p:
        room['timer_cancel'] = True
        socketio.sleep(0.4)
        do_show_results(code)

@socketio.on('next-question')
def on_next(data):
    code = data.get('roomCode')
    if code not in rooms: return
    room = rooms[code]
    if request.sid != room['host_sid']: return
    room['current_idx']  += 1
    room['timer_cancel']  = False
    if room['current_idx'] >= len(room['questions']):
        end_game(code)
    else:
        send_question(code)

@socketio.on('force-results')
def on_force(data):
    code = data.get('roomCode')
    if code not in rooms: return
    if request.sid != rooms[code]['host_sid']: return
    rooms[code]['timer_cancel'] = True
    socketio.sleep(0.2)
    do_show_results(code)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    for code, room in list(rooms.items()):
        if sid not in room['players']: continue
        player = room['players'].pop(sid, None)
        if not player: continue
        if sid == room['host_sid']:
            room['timer_cancel'] = True
            socketio.emit('host-disconnected', {}, to=code)
            def _clean(c=code):
                socketio.sleep(30)
                rooms.pop(c, None)
            socketio.start_background_task(_clean)
        else:
            socketio.emit('player-left', {'username': player['username'], **room_pub(room)}, to=code)
        break

# ═════════════════════════════════════════════════════════════
#  GAME ENGINE
# ═════════════════════════════════════════════════════════════

def send_question(code):
    room = rooms.get(code)
    if not room: return
    q = room['questions'][room['current_idx']]
    room.update({'current_q': q, 'state': 'question', 'q_answers': {}, 'timer_cancel': False})
    socketio.emit('new-question', {
        'question':       {'id': q['id'], 'question_text': q['question_text'],
                           'options': q['answer_options'], 'time_limit': q['time_limit']},
        'questionNumber': room['current_idx'] + 1,
        'totalQuestions': len(room['questions']),
        'teamScores':     room['team_scores'],
    }, to=code)

    def run_timer(q_id=q['id'], tl=q['time_limit']):
        socketio.sleep(1)
        rooms[code]['q_start_ms'] = time.time() * 1000
        for tick in range(tl):
            socketio.sleep(1)
            r = rooms.get(code)
            if not r or r.get('timer_cancel') or r['state'] != 'question': return
            if r['current_q']['id'] != q_id: return
            left = tl - tick - 1
            socketio.emit('timer-tick', {'timeLeft': left, 'total': tl}, to=code)
            if left == 0:
                do_show_results(code); return

    socketio.start_background_task(run_timer)


def do_show_results(code):
    room = rooms.get(code)
    if not room or room['state'] in ('results', 'gameover'): return
    room['state'] = 'results'
    q = room['current_q']
    results = sorted([{
        'socketId':   p['socketId'], 'username': p['username'],
        'team': p['team'], 'avatar': p['avatar'], 'totalScore': p['score'],
        'answerIndex': room['q_answers'].get(p['socketId'], {}).get('answerIndex', -1),
        'isCorrect':   room['q_answers'].get(p['socketId'], {}).get('isCorrect', False),
        'points':      room['q_answers'].get(p['socketId'], {}).get('points', 0),
        'streak': p['streak'], 'isHost': p['isHost'],
    } for p in room['players'].values()], key=lambda x: -x['totalScore'])

    socketio.emit('question-results', {
        'correctAnswer':     q['correct_answer'],
        'correctAnswerText': q['answer_options'][q['correct_answer']],
        'playerResults': results,
        'teamA': [r for r in results if r['team'] == 'A'],
        'teamB': [r for r in results if r['team'] == 'B'],
        'teamScores':    room['team_scores'],
        'isLastQuestion': room['current_idx'] >= len(room['questions']) - 1,
        'questionNumber': room['current_idx'] + 1,
        'totalQuestions': len(room['questions']),
    }, to=code)


def end_game(code):
    room = rooms.get(code)
    if not room: return
    room['state'] = 'gameover'
    room['timer_cancel'] = True
    s = room['team_scores']
    winner = 'A' if s['A'] > s['B'] else ('B' if s['B'] > s['A'] else 'DRAW')
    players = sorted(room['players'].values(), key=lambda p: -p['score'])

    try:
        wc = 1 if winner == 'A' else (2 if winner == 'B' else 0)
        host_uid = next((p['userId'] for p in players if p['isHost']), None)

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''INSERT INTO game_sessions
                       (room_code, topic_id, host_user_id, host_name,
                        total_questions, team_a_score, team_b_score,
                        winner_team, player_count, ended_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())''',
                    (code, room['topic']['id'], host_uid, room['host_name'],
                     len(room['questions']), s['A'], s['B'], wc, len(players))
                )
                sess_id = cur.lastrowid

                for p in players:
                    team_num = 1 if p['team'] == 'A' else 2
                    cur.execute(
                        '''INSERT INTO session_players
                           (session_id, user_id, guest_name, team, final_score, is_host)
                           VALUES (%s,%s,%s,%s,%s,%s)''',
                        (sess_id, p['userId'],
                         None if p['userId'] else p['username'],
                         team_num, p['score'], 1 if p['isHost'] else 0)
                    )
                    if p['userId']:
                        won = 1 if p['team'] == winner else 0
                        cur.execute(
                            'UPDATE users SET games_played=games_played+1, games_won=games_won+%s, total_score=total_score+%s WHERE id=%s',
                            (won, p['score'], p['userId'])
                        )
                conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f'[DB] end_game error: {e}')

    socketio.emit('game-over', {
        'winner': winner, 'teamScores': s,
        'playerResults': [{'username': p['username'], 'team': p['team'],
                           'avatar': p['avatar'], 'score': p['score'], 'isHost': p['isHost']}
                          for p in players],
    }, to=code)

    def _clean(c=code):
        socketio.sleep(600)
        rooms.pop(c, None)
    socketio.start_background_task(_clean)


# ═════════════════════════════════════════════════════════════
if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    print(f'Servidor corriendo en http://0.0.0.0:{port}')
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
