from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

def obtener_noticias(filtro_texto="", filtro_autor=""):
    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()
    
    query = "SELECT titulo, enlace, fecha, autor FROM noticias WHERE 1=1"
    params = []
    
    if filtro_texto:
        query += " AND titulo LIKE ?"
        params.append(f"%{filtro_texto}%")
    if filtro_autor:
        query += " AND autor = ?"
        params.append(filtro_autor)
    
    cursor.execute(query, params)
    noticias = cursor.fetchall()
    conn.close()
    return noticias

def obtener_autores():
    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT autor FROM noticias")
    autores = [row[0] for row in cursor.fetchall()]
    conn.close()
    return autores

@app.route("/", methods=["GET"])
def index():
    texto = request.args.get("texto", "")
    autor = request.args.get("autor", "")
    
    noticias = obtener_noticias(texto, autor)
    autores = obtener_autores()
    
    return render_template(
        "index.html",
        noticias=noticias,
        autores=autores,
        filtro_texto=texto,
        filtro_autor=autor
    )

if __name__ == "__main__":
    app.run(debug=True)
