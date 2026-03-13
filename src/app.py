"""
TeamKahoot — Backend (Railway)
VERSIÓN SIMPLIFICADA Y FUNCIONAL
"""

import os, random, time, json
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import pymysql
import pymysql.cursors
import bcrypt
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'kahoot-secret-2024')

# CORS - Simple y directo
CORS(app, resources={r"/*": {"origins": "*"}})

# Socket.IO - Simple y funcional
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)

# Database
def parse_db_url(url):
    p = urlparse(url)
    return {
        'host': p.hostname,
        'port': p.port or 3306,
        'user': p.username,
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
                if result is None and cur.lastrowid:
                    result = {'id': cur.lastrowid}
    finally:
        conn.close()
    return result

def query_returning(sql, params, returning_sql, returning_params):
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

# Game rooms
rooms = {}
CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

def make_code():
    while True:
        code = ''.join(random.choices(CHARS, k=6))
        if code not in rooms:
            return code

HARDCODED_QUESTIONS = {
    'prog': [
        {'id':'p1', 'question_text':'¿Qué significa "bug" en programación?', 'answer_options':['Un error en el código','Un tipo de variable','Un lenguaje','Un ejecutable'], 'correct_answer':0,'time_limit':20},
        {'id':'p2', 'question_text':'¿Qué es un algoritmo?', 'answer_options':['Un tipo de base de datos','Una serie de pasos para resolver un problema','Un SO','Un IDE'], 'correct_answer':1,'time_limit':20},
        {'id':'p3', 'question_text':'¿Qué tipo de dato almacena números enteros?', 'answer_options':['String','Boolean','Integer','Float'], 'correct_answer':2,'time_limit':15},
        {'id':'p4', 'question_text':'¿Qué hace un bucle "while"?', 'answer_options':['Declara variables','Repite mientras condición sea verdadera','Crea funciones','Importa librerías'], 'correct_answer':1,'time_limit':20},
        {'id':'p5', 'question_text':'¿Qué es la recursividad?', 'answer_options':['Un tipo de bucle for','Cuando una función se llama a sí misma','Un patrón de diseño','Un tipo de variable'], 'correct_answer':1,'time_limit':20},
        {'id':'p6', 'question_text':'¿Qué es una variable?', 'answer_options':['Un tipo de función','Un espacio en memoria para almacenar datos','Un operador lógico','Un protocolo'], 'correct_answer':1,'time_limit':15},
        {'id':'p7', 'question_text':'¿Qué significa POO?', 'answer_options':['Programación Orientada a Objetos','Proceso Operativo Optimizado','Protocolo Online','Plataforma Offline'], 'correct_answer':0,'time_limit':20},
        {'id':'p8', 'question_text':'¿Qué es la herencia en POO?', 'answer_options':['Copiar código','Una clase recibe atributos de otra','Eliminar variables','Un tipo de bucle'], 'correct_answer':1,'time_limit':20},
        {'id':'p9', 'question_text':'¿Qué es un IDE?', 'answer_options':['Una base de datos','Un protocolo','Un entorno de desarrollo integrado','Control de versiones'], 'correct_answer':2,'time_limit':15},
        {'id':'p10','question_text':'¿Qué hace el operador AND lógico?', 'answer_options':['True si una condición es verdadera','True solo si ambas son verdaderas','Niega una condición','Compara strings'], 'correct_answer':1,'time_limit':20},
    ],
    'html': [
        {'id':'h1', 'question_text':'¿Qué significa HTML?', 'answer_options':['HyperText Markup Language','High Transfer Markup Language','Hyperlink and Text Markup Language','Home Tool Markup Language'], 'correct_answer':0,'time_limit':15},
        {'id':'h2', 'question_text':'¿Qué etiqueta es el título principal de una página?','answer_options':['<title>','<head>','<h1>','<header>'], 'correct_answer':2,'time_limit':15},
        {'id':'h3', 'question_text':'¿Cuál es la etiqueta correcta para un hipervínculo?','answer_options':['<link>','<a>','<href>','<url>'], 'correct_answer':1,'time_limit':15},
        {'id':'h4', 'question_text':'¿Qué etiqueta se usa para insertar una imagen?', 'answer_options':['<picture>','<photo>','<image>','<img>'], 'correct_answer':3,'time_limit':15},
        {'id':'h5', 'question_text':'¿Qué atributo define el destino de un enlace <a>?','answer_options':['src','link','href','url'], 'correct_answer':2,'time_limit':15},
        {'id':'h6', 'question_text':'¿Qué etiqueta crea una lista desordenada?', 'answer_options':['<ol>','<list>','<ul>','<dl>'], 'correct_answer':2,'time_limit':15},
        {'id':'h7', 'question_text':'¿Qué etiqueta define el cuerpo del documento HTML?','answer_options':['<main>','<body>','<content>','<section>'], 'correct_answer':1,'time_limit':15},
        {'id':'h8', 'question_text':'¿Cuál es la etiqueta para crear una tabla?', 'answer_options':['<table>','<grid>','<tab>','<tr>'], 'correct_answer':0,'time_limit':15},
        {'id':'h9', 'question_text':'¿Qué etiqueta se usa para negrita?', 'answer_options':['<bold>','<strong>','<b>','Ambas <b> y <strong>'], 'correct_answer':3,'time_limit':20},
        {'id':'h10','question_text':'¿Dónde se pone el <script> para mejor rendimiento?','answer_options':['En el <head>','Al inicio del <body>','Al final del <body>','No importa'], 'correct_answer':2,'time_limit':20},
    ],
    'js': [
        {'id':'j1', 'question_text':'¿Cómo se declara una variable en JS moderno?', 'answer_options':['Solo var','Solo let','Solo const','var, let y const son válidas'], 'correct_answer':3,'time_limit':15},
        {'id':'j2', 'question_text':'¿Qué método agrega un elemento al final de un array?','answer_options':['push()','pop()','shift()','append()'], 'correct_answer':0,'time_limit':15},
        {'id':'j3', 'question_text':'¿Qué hace console.log()?', 'answer_options':['Guarda en BD','Imprime en la consola','Crea un alert','Envía al servidor'], 'correct_answer':1,'time_limit':15},
        {'id':'j4', 'question_text':'¿Qué es una función arrow?', 'answer_options':['Una función con nombre','Sintaxis corta: () => {}','Un tipo de bucle','Un método de array'], 'correct_answer':1,'time_limit':20},
        {'id':'j5', 'question_text':'¿Qué retorna typeof null?', 'answer_options':['"null"','"undefined"','"object"','"boolean"'], 'correct_answer':2,'time_limit':20},
        {'id':'j6', 'question_text':'¿Diferencia entre == y ===?', 'answer_options':['No hay diferencia','== valor, === valor y tipo','=== solo números','== es más estricto'], 'correct_answer':1,'time_limit':20},
        {'id':'j7', 'question_text':'¿Qué es el DOM?', 'answer_options':['Un framework','Document Object Model','Una base de datos','Un protocolo HTTP'], 'correct_answer':1,'time_limit':20},
        {'id':'j8', 'question_text':'¿Qué hace el método map() en un array?', 'answer_options':['Filtra elementos','Retorna un nuevo array transformado','Ordena','Busca un elemento'], 'correct_answer':1,'time_limit':15},
        {'id':'j9', 'question_text':'¿Qué es una Promesa (Promise) en JS?', 'answer_options':['Una variable constante','Un valor futuro asíncrono','Un tipo de bucle','Una función recursiva'], 'correct_answer':1,'time_limit':20},
        {'id':'j10','question_text':'¿Qué hace JSON.parse()?', 'answer_options':['Objeto JS a string JSON','String JSON a objeto JS','Valida un JSON','Envía JSON'], 'correct_answer':1,'time_limit':15},
    ],
    'drama': [
        {'id':'d1', 'question_text':'¿Cuántos años dura el programa de informática?', 'answer_options':['3 años (4to, 5to y 6to año)','4 años (3ro al 6to, con práctica extendida)','2 años intensivos con pasantías','5 años incluyendo un año de servicio social'], 'correct_answer':0,'time_limit':20},
        {'id':'d2', 'question_text':'¿Cuántas horas totales tiene la carga horaria del programa de informática?', 'answer_options':['3600 horas distribuidas en 3 años','4680 horas en módulos teórico-prácticos','5200 horas con especialidad avanzada','2400 horas solo de laboratorio'], 'correct_answer':1,'time_limit':20},
        {'id':'d3', 'question_text':'¿En qué nivel se estudia el Bachillerato Técnico en Informática?', 'answer_options':['Nivel 1 (básico)','Nivel 2 (intermedio)','Nivel 3 (técnico)','Nivel 4 (superior)'], 'correct_answer':2,'time_limit':20},
        {'id':'d4', 'question_text':'¿En qué sector principal se puede trabajar con este programa de informática?', 'answer_options':['Manufactura e Industria (producción automatizada)','Salud y Bienestar (clínicas y laboratorios)','Construcción y Obra (planos y cálculos)','Servicios e Informática (soporte, desarrollo y redes)'], 'correct_answer':3,'time_limit':20},
        {'id':'d5', 'question_text':'¿Cuál es un beneficio importante del programa de informática?', 'answer_options':['Horario reducido sin prácticas','Alta demanda laboral y múltiples salidas','Solo trabajo en casa con horarios fijos','No requiere actualización constante'], 'correct_answer':1,'time_limit':20},
        {'id':'d6', 'question_text':'¿En qué área se puede trabajar ayudando a usuarios de computadoras?', 'answer_options':['Diseño gráfico y edición de video','Asistencia y soporte al usuario de TI','Contabilidad digital y auditoría','Seguridad física y vigilancia'], 'correct_answer':1,'time_limit':20},
        {'id':'d7', 'question_text':'¿Qué es la informática?', 'answer_options':['Solo el uso de internet y redes sociales','Reparar teléfonos móviles y tablets','Ciencia que procesa, almacena y transmite información usando computadoras','Diseñar ropa con tecnología y telas inteligentes'], 'correct_answer':2,'time_limit':20},
        {'id':'d8', 'question_text':'¿Por qué la informática es una de las áreas más importantes hoy en día?', 'answer_options':['Porque es la materia más fácil y rápida','Porque solo se usa en hospitales y bancos','Porque no requiere estudiar ni capacitarse','Porque casi todas las empresas y organizaciones usan tecnología'], 'correct_answer':3,'time_limit':20},
        {'id':'d9', 'question_text':'Menciona dos herramientas que usamos todos los días gracias a la informática.', 'answer_options':['Aplicaciones móviles y redes sociales','Calculadoras y lápices de dibujo','Libros impresos y mapas de papel','Martillos y tornillos de obra'], 'correct_answer':0,'time_limit':20},
        {'id':'d10', 'question_text':'¿La informática es solo usar computadoras?', 'answer_options':['Sí, solo se trata de usar computadoras en casa','No, es mucho más que usar computadoras','Sí, solo es programar videojuegos','No, solo se trata de redes y cableado'], 'correct_answer':1,'time_limit':20},
        {'id':'d11', 'question_text':'Menciona dos áreas profesionales de la informática.', 'answer_options':['Medicina y enfermería con software clínico','Contabilidad y finanzas con hojas de cálculo','Programación y redes informáticas','Arquitectura y diseño de interiores'], 'correct_answer':2,'time_limit':20},
        {'id':'d12', 'question_text':'¿Qué se aprende en el área de informática?', 'answer_options':['Solo a escribir documentos y presentaciones','Solo a navegar por internet con seguridad básica','Solo a usar redes sociales en clase','Crear programas, diseñar páginas web, reparar computadoras y administrar redes'], 'correct_answer':3,'time_limit':20},
        {'id':'d13', 'question_text':'¿Qué trabajo hace un programador?', 'answer_options':['Crear programas y aplicaciones usando lenguajes de programación','Reparar cables de red y conectores','Diseñar edificios con software CAD','Vender computadoras en tiendas y ferias'], 'correct_answer':0,'time_limit':20},
        {'id':'d14', 'question_text':'¿Qué hace un técnico de redes?', 'answer_options':['Solo repara impresoras y periféricos','Programa videojuegos para móviles','Conecta computadoras, configura routers/servidores y asegura la red','Diseña páginas web únicamente'], 'correct_answer':2,'time_limit':20},
        {'id':'d15', 'question_text':'¿Qué frase dicen al final del drama sobre la informática?', 'answer_options':['"La tecnología nos destruirá" y no hay solución','"El pasado es la informática" como mensaje histórico','"El futuro es la informática"','"La informática no es para todos" como advertencia'], 'correct_answer':2,'time_limit':20},
        {'id':'d16', 'question_text':'TRAMPA: ¿Cuál de estas NO es una tarea típica de un técnico en informática?', 'answer_options':['Configurar redes y equipos','Dar soporte a usuarios','Diseñar edificios y planos arquitectónicos','Instalar software y sistemas'], 'correct_answer':2,'time_limit':20},
        {'id':'d17', 'question_text':'TRAMPA: ¿Cuál opción suena correcta pero es falsa sobre programación?', 'answer_options':['Se usan lenguajes para crear software','Se prueba y corrige el codigo','Solo sirve para videojuegos','Se trabaja con algoritmos'], 'correct_answer':2,'time_limit':20},
        {'id':'d18', 'question_text':'TRAMPA: ¿Qué afirmación es incorrecta sobre redes?', 'answer_options':['Se usan routers y switches','Permiten compartir internet','Solo funcionan sin cables','Requieren configuracion'], 'correct_answer':2,'time_limit':20},
        {'id':'d19', 'question_text':'TRAMPA: ¿Cuál NO es un ejemplo de herramienta informática cotidiana?', 'answer_options':['Aplicaciones de mensajeria','Redes sociales','Planos de construccion en papel','Plataformas de aprendizaje'], 'correct_answer':2,'time_limit':20},
        {'id':'d20', 'question_text':'TRAMPA: ¿Cuál afirmación sobre el programa de informática es falsa?', 'answer_options':['Incluye practicas tecnicas','Tiene alta demanda laboral','No necesita actualizacion','Ofrece varias salidas'], 'correct_answer':2,'time_limit':20},
    ],
}

HARDCODED_TOPICS = {
    'prog': {'id':'prog','name':'Programación General','icon_code':2},
    'html': {'id':'html','name':'HTML','icon_code':1},
    'js':   {'id':'js',  'name':'JavaScript','icon_code':2},
    'drama':{'id':'drama','name':'Drama y Exposición','icon_code':1},
}

def get_questions(topic_id):
    import copy as _copy, random as _r
    qs = _copy.deepcopy(HARDCODED_QUESTIONS.get(str(topic_id), []))
    _r.shuffle(qs)
    return qs

def _active_players(room):
    return [p for p in room['players'].values() if not p.get('isHost')]

def room_pub(room):
    players = _active_players(room)
    return {
        'code': room['code'],
        'topic': room['topic'],
        'teamA': [p for p in players if p['team'] == 'A'],
        'teamB': [p for p in players if p['team'] == 'B'],
        'players': players,
        'state': room['state'],
    }

def next_team(room):
    return 'A' if len(_active_players(room)) % 2 == 0 else 'B'

# REST API
@app.route('/')
def serve_index():
    return send_from_directory(os.path.dirname(__file__), 'index.html')

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify(error='Not Found'), 404
    return send_from_directory(os.path.dirname(__file__), 'index.html')

@app.route('/api/health')
def health():
    return jsonify(status='ok')

@app.route('/api/register', methods=['POST'])
def register():
    d = request.json or {}
    username = (d.get('username') or '').strip()
    email = (d.get('email') or '').strip().lower()
    password = d.get('password') or ''

    if not username or not email or not password:
        return jsonify(error='Todos los campos son obligatorios'), 400
    if len(username) < 3:
        return jsonify(error='El nombre debe tener al menos 3 caracteres'), 400
    if len(password) < 6:
        return jsonify(error='La contrasena debe tener al menos 6 caracteres'), 400
    try:
        exists = query('SELECT id FROM users WHERE email=%s OR username=%s', (email, username), fetchone=True)
        if exists:
            return jsonify(error='Email o nombre de usuario ya en uso'), 409

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        avatar = random.randint(1, 8)

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
    d = request.json or {}
    email = (d.get('email') or '').strip().lower()
    password = d.get('password') or ''
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
        rows = query('SELECT username,total_score,games_played,games_won FROM users ORDER BY total_score DESC LIMIT 10', fetchall=True)
        return jsonify(rows)
    except Exception as e:
        return jsonify(error=str(e)), 500

# SOCKET.IO EVENTS
@socketio.on('connect')
def on_connect():
    print(f'[Socket] Client connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    print(f'[Socket] Client disconnected: {request.sid}')
    sid = request.sid
    for code in list(rooms.keys()):
        room = rooms[code]
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

@socketio.on('create-room')
def on_create_room(data):
    topic_id = data.get('topicId')
    host_name = (data.get('hostName') or 'Anfitrion').strip()
    user_id = data.get('userId')

    topic = HARDCODED_TOPICS.get(str(topic_id))
    if not topic:
        emit('error', {'msg': f'Tema no encontrado: {topic_id}'}); return

    questions = get_questions(topic_id)
    if not questions:
        emit('error', {'msg': 'Sin preguntas para este tema'}); return

    code = make_code()
    avatar = random.randint(1, 8)
    player = {
        'socketId': request.sid, 'userId': user_id,
        'username': host_name, 'team': None,
        'score': 0, 'streak': 0, 'avatar': avatar, 'isHost': True,
    }
    rooms[code] = {
        'code': code, 'topic': topic, 'questions': questions,
        'host_sid': request.sid, 'host_name': host_name,
        'host_user_id': user_id,
        'players': {request.sid: player},
        'state': 'waiting',
        'current_idx': -1, 'current_q': None,
        'q_answers': {}, 'team_scores': {'A': 0, 'B': 0},
        'q_start_ms': None, 'timer_cancel': False,
    }
    join_room(code)
    emit('room-created', {
        'roomCode': code, 'topic': topic, 'questionCount': len(questions),
        'player': player, 'room': room_pub(rooms[code])
    })
    print(f'[Room] Created: {code}')

@socketio.on('join-room')
def on_join_room(data):
    code = (data.get('roomCode') or '').upper().strip()
    username = (data.get('username') or 'Player').strip()
    user_id = data.get('userId')

    room = rooms.get(code)
    if not room:
        emit('join-error', {'msg': 'Código de sala inválido'}); return
    if room['state'] != 'waiting':
        emit('join-error', {'msg': 'La sala no está disponible'}); return

    team = next_team(room)
    avatar = random.randint(1, 8)
    player = {
        'socketId': request.sid, 'userId': user_id,
        'username': username, 'team': team,
        'score': 0, 'streak': 0, 'avatar': avatar, 'isHost': False,
    }
    room['players'][request.sid] = player
    join_room(code)
    emit('joined-room', {'player': player, 'room': room_pub(room)})
    socketio.emit('player-joined', {'player': player, **room_pub(room)}, to=code, skip_sid=request.sid)
    print(f'[Room] {code}: {username} joined ({team})')

@socketio.on('start-game')
def on_start_game(data):
    code = data.get('roomCode')
    room = rooms.get(code)
    if not room or request.sid != room['host_sid']:
        emit('error', {'msg': 'No autorizado'}); return
    if len(_active_players(room)) < 2:
        emit('error', {'msg': 'Mínimo 2 jugadores'}); return
    
    room['state'] = 'countdown'
    socketio.emit('countdown-tick', {'countdown': 3}, to=code)
    
    def _countdown():
        for i in range(2, 0, -1):
            socketio.sleep(1)
            if rooms.get(code):
                socketio.emit('countdown-tick', {'countdown': i}, to=code)
        if rooms.get(code):
            room = rooms[code]
            room['current_idx'] = 0
            send_question(code)
    
    socketio.start_background_task(_countdown)

@socketio.on('submit-answer')
def on_submit_answer(data):
    code = data.get('roomCode')
    ans_idx = data.get('answerIndex')
    room = rooms.get(code)
    if not room or room['state'] != 'question': return
    
    player = room['players'].get(request.sid)
    if not player: return
    if player.get('isHost'): return
    
    q = room['current_q']
    is_correct = ans_idx == q['correct_answer']
    
    elapsed_ms = time.time() * 1000 - room['q_start_ms']
    max_ms = q['time_limit'] * 1000
    points = max(0, int(1000 * (1 - elapsed_ms / max_ms))) if is_correct else 0
    
    if is_correct:
        player['streak'] += 1
        points += player['streak'] * 50
    else:
        player['streak'] = 0
    
    player['score'] += points
    team = player['team']
    room['team_scores'][team] += points
    
    room['q_answers'][request.sid] = {'answerIndex': ans_idx, 'isCorrect': is_correct, 'points': points}
    
    emit('answer-result', {'isCorrect': is_correct, 'points': points, 'correctAnswer': q['correct_answer'], 'streak': player['streak']})
    socketio.emit('answer-count', {'answered': len(room['q_answers']), 'total': len(_active_players(room))}, to=code)

@socketio.on('next-question')
def on_next_question(data):
    code = data.get('roomCode')
    room = rooms.get(code)
    if not room or request.sid != room['host_sid']:
        emit('error', {'msg': 'No autorizado'}); return
    
    room['current_idx'] += 1
    if room['current_idx'] >= len(room['questions']):
        end_game(code)
    else:
        send_question(code)

@socketio.on('force-results')
def on_force_results(data):
    code = data.get('roomCode')
    room = rooms.get(code)
    if not room: return
    if request.sid == room['host_sid']:
        room['timer_cancel'] = True
        do_show_results(code)

def send_question(code):
    room = rooms.get(code)
    if not room: return
    q = room['questions'][room['current_idx']]
    room.update({'current_q': q, 'state': 'question', 'q_answers': {}, 'timer_cancel': False})
    socketio.emit('new-question', {
        'question': {'id': q['id'], 'question_text': q['question_text'], 'options': q['answer_options'], 'time_limit': q['time_limit']},
        'questionNumber': room['current_idx'] + 1,
        'totalQuestions': len(room['questions']),
        'teamScores': room['team_scores'],
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
        'socketId': p['socketId'], 'username': p['username'],
        'team': p['team'], 'avatar': p['avatar'], 'totalScore': p['score'],
        'answerIndex': room['q_answers'].get(p['socketId'], {}).get('answerIndex', -1),
        'isCorrect': room['q_answers'].get(p['socketId'], {}).get('isCorrect', False),
        'points': room['q_answers'].get(p['socketId'], {}).get('points', 0),
        'streak': p['streak'], 'isHost': p['isHost'],
    } for p in _active_players(room)], key=lambda x: -x['totalScore'])

    socketio.emit('question-results', {
        'correctAnswer': q['correct_answer'],
        'correctAnswerText': q['answer_options'][q['correct_answer']],
        'playerResults': results,
        'teamA': [r for r in results if r['team'] == 'A'],
        'teamB': [r for r in results if r['team'] == 'B'],
        'teamScores': room['team_scores'],
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
    players = sorted(_active_players(room), key=lambda p: -p['score'])

    try:
        wc = 1 if winner == 'A' else (2 if winner == 'B' else 0)
        host_uid = room.get('host_user_id')

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO game_sessions (room_code, topic_id, host_user_id, host_name, total_questions, team_a_score, team_b_score, winner_team, player_count, ended_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())',
                    (code, room['topic']['id'], host_uid, room['host_name'], len(room['questions']), s['A'], s['B'], wc, len(players))
                )
                sess_id = cur.lastrowid
                for p in players:
                    team_num = 1 if p['team'] == 'A' else 2
                    cur.execute(
                        'INSERT INTO session_players (session_id, user_id, guest_name, team, final_score, is_host) VALUES (%s,%s,%s,%s,%s,%s)',
                        (sess_id, p['userId'], None if p['userId'] else p['username'], team_num, p['score'], 0)
                    )
                    if p['userId']:
                        won = 1 if p['team'] == winner else 0
                        cur.execute('UPDATE users SET games_played=games_played+1, games_won=games_won+%s, total_score=total_score+%s WHERE id=%s', (won, p['score'], p['userId']))
                conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f'[DB] Error: {e}')

    socketio.emit('game-over', {
        'winner': winner, 'teamScores': s,
        'playerResults': [{'username': p['username'], 'team': p['team'], 'avatar': p['avatar'], 'score': p['score'], 'isHost': p['isHost']} for p in players],
    }, to=code)

    def _clean(c=code):
        socketio.sleep(600)
        rooms.pop(c, None)
    socketio.start_background_task(_clean)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
