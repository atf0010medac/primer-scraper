# app_oposiciones.py

from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging

# --------------------
# Configuración
# --------------------
DB_PATH = 'oposiciones.db'
app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --------------------
# Base de datos
# --------------------
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
    db.commit()


# --------------------
# Scraper BOE últimos 7 días
# --------------------
def scrape_boe(days=7):
    """Raspa la sección 2B del BOE de los últimos `days` días."""
    init_db()
    db = get_db()
    total_collected = 0

    for i in range(days):
        dia = datetime.today() - timedelta(days=i)
        fecha_str = dia.strftime("%Y%m%d")
        url_boe = f'https://www.boe.es/datosabiertos/api/boe/sumario/{fecha_str}'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/118.0.5993.118 Safari/537.3',
            'Accept': 'application/xml, text/xml, */*; q=0.01'
        }

        try:
            r = requests.get(url_boe, headers=headers, timeout=10)
            r.raise_for_status()
        except requests.RequestException as e:
            logging.warning(f"No se pudo obtener XML para {fecha_str}: {e}")
            continue

        soup = BeautifulSoup(r.content, 'xml')
        seccion = soup.find("seccion", {"codigo": "2B"})
        if not seccion:
            continue

        for item in seccion.find_all("item"):
            identificador = item.find("identificador").text.strip() if item.find("identificador") else None
            control = item.find("control").text.strip() if item.find("control") else None
            titulo = item.find("titulo").text.strip() if item.find("titulo") else None
            url_html = item.find("url_html").text.strip() if item.find("url_html") else None
            url_pdf = item.find("url_pdf").text.strip() if item.find("url_pdf") else None
            dept_parent = item.find_parent("departamento")
            departamento = dept_parent.get('nombre') if dept_parent and dept_parent.has_attr('nombre') else None

            if not identificador or not url_html:
                continue

            try:
                db.execute('''
                    INSERT INTO oposiciones (identificador, control, titulo, url_html, url_pdf, departamento, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (identificador, control, titulo, url_html, url_pdf, departamento, fecha_str))
                db.commit()
                total_collected += 1
            except sqlite3.IntegrityError:
                continue  # Entrada duplicada

    logging.info(f"Scraping completado. Nuevas oposiciones añadidas: {total_collected}")
    return total_collected


# --------------------
# Rutas Flask
# --------------------
@app.route('/')
def index():
    init_db()
    db = get_db()

    # Obtener filtros del usuario
    q = request.args.get('q', '').strip()
    departamento = request.args.get('departamento', '').strip()
    fecha = request.args.get('fecha', '').strip()

    sql = 'SELECT * FROM oposiciones'
    params = []
    where = []

    if q:
        likeq = f'%{q}%'
        where.append("(identificador LIKE ? OR control LIKE ? OR titulo LIKE ?)")
        params.extend([likeq, likeq, likeq])

    if departamento:
        where.append("departamento = ?")
        params.append(departamento)

    if fecha:
        where.append("fecha = ?")
        params.append(fecha.replace('-', ''))

    if where:
        sql += ' WHERE ' + ' AND '.join(where)

    # Ordenar por fecha descendente y luego id descendente
    sql += ' ORDER BY fecha DESC, id DESC'

    rows = db.execute(sql, params).fetchall()

    # Lista de departamentos para el filtro
    departamentos = db.execute(
        'SELECT DISTINCT departamento FROM oposiciones WHERE departamento IS NOT NULL ORDER BY departamento'
    ).fetchall()

    return render_template(
        'index.html',
        rows=rows,
        q=q,
        departamento=departamento,
        fecha=fecha,
        departamentos=departamentos
    )



@app.route('/scrape')
def trigger_scrape():
    with app.app_context():
        scrape_boe()
    return redirect(url_for('index'))


# --------------------
# Inicio de la app
# --------------------
if __name__ == '__main__':
    with app.app_context():
        init_db()
        scrape_boe()  # Rellena la BD con últimos 7 días automáticamente al iniciar
    app.run(debug=True)
