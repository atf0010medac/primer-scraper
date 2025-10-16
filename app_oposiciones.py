from flask import Flask, render_template, request, redirect, url_for, g, session, flash
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = 'oposiciones.db'
app = Flask(__name__)
app.secret_key = 'clave_super_segura'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ------------------ BASE DE DATOS ------------------ #

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db:
        db.close()

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS oposiciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identificador TEXT NOT NULL,
            control TEXT,
            titulo TEXT,
            url_html TEXT UNIQUE,
            url_pdf TEXT,
            departamento TEXT,
            fecha TEXT
        )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    db.commit()

# ------------------ SCRAPING ------------------ #

def scrape_boe(days=7):
    init_db()
    db = get_db()
    total_collected = 0

    for i in range(days):
        dia = datetime.today() - timedelta(days=i)
        fecha_str = dia.strftime("%Y%m%d")
        url_boe = f'https://www.boe.es/datosabiertos/api/boe/sumario/{fecha_str}'

        try:
            r = requests.get(url_boe, timeout=10)
            r.raise_for_status()
        except requests.RequestException as e:
            logging.warning(f"No se pudo obtener XML para {fecha_str}: {e}")
            continue

        soup = BeautifulSoup(r.content, 'xml')
        seccion = soup.find("seccion", {"codigo": "2B"})
        if not seccion:
            continue

        items = seccion.find_all("item")
        logging.info(f"Fecha {fecha_str}: {len(items)} items encontrados")

        for item in items:
            identificador = item.findtext("identificador")
            control = item.findtext("control")
            titulo = item.findtext("titulo")
            url_html = item.findtext("url_html")
            url_pdf = item.findtext("url_pdf")

            departamento = None
            dep_tag = item.find_parent("departamento") or item.find("departamento")
            if dep_tag:
                departamento = dep_tag.get("nombre") or dep_tag.text.strip()

            if not identificador or not url_html or not departamento:
                continue

            try:
                db.execute('''
                    INSERT INTO oposiciones (identificador, control, titulo, url_html, url_pdf, departamento, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (identificador, control, titulo, url_html, url_pdf, departamento, fecha_str))
                db.commit()
                total_collected += 1
            except sqlite3.IntegrityError:
                continue

    logging.info(f"Scraping completado. Nuevas oposiciones añadidas: {total_collected}")
    return total_collected

# ------------------ RUTAS ------------------ #

@app.route('/')
def index():
    init_db()
    db = get_db()

    departamentos = db.execute('''
        SELECT departamento, MAX(fecha) AS ultima_fecha
        FROM oposiciones
        WHERE departamento IS NOT NULL AND TRIM(departamento) != ''
        GROUP BY departamento
        ORDER BY ultima_fecha DESC
    ''').fetchall()

    return render_template('index.html', departamentos=departamentos)

@app.route('/departamento/<nombre>')
def ver_departamento(nombre):
    db = get_db()

    q = request.args.get('q', '').strip()
    fecha = request.args.get('fecha', '').strip()

    sql = 'SELECT * FROM oposiciones WHERE departamento = ?'
    params = [nombre]

    if q:
        likeq = f'%{q}%'
        sql += ' AND (titulo LIKE ? OR identificador LIKE ? OR control LIKE ?)'
        params.extend([likeq, likeq, likeq])

    if fecha:
        sql += ' AND fecha = ?'
        params.append(fecha.replace('-', ''))

    sql += ' ORDER BY fecha DESC, id DESC'

    rows = db.execute(sql, params).fetchall()

    return render_template('departamento.html', nombre=nombre, rows=rows, q=q, fecha=fecha)

@app.route('/scrape')
def trigger_scrape():
    with app.app_context():
        scrape_boe()
    return redirect(url_for('index'))

# ------------------ LOGIN / REGISTRO ------------------ #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user'] = user['nombre']
            return redirect(url_for('index'))
        else:
            flash("Credenciales incorrectas", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db()
        try:
            db.execute("INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)",
                       (nombre, email, password))
            db.commit()
            flash("Registro completado. Ahora puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("El correo ya está registrado.", "danger")

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# ------------------ MAIN ------------------ #

if __name__ == '__main__':
    with app.app_context():
        init_db()
        scrape_boe()
    app.run(debug=True)
