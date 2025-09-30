from bs4 import BeautifulSoup
import requests
import sqlite3
import re

# URLs del scraper
urls = [
    "https://www.marca.com/futbol.html?intcmp=MENUPROD&s_kw=futbol",
    "https://www.marca.com/futbol/real-madrid/2025/09/24/madrid-llega-lanzado-derbi.html",
    "https://www.marca.com/futbol/primera-division/2025/09/24/atletico-rayo-vallecano-derbi-crucial-gran-derbi.html",
    "https://www.marca.com/futbol/primera-division/2025/09/23/getafe-alaves-mirar-abajo-previa-analisis-pronostico-prediccion.html",
    "https://www.marca.com/futbol/primera-division/2025/09/24/real-sociedad-mallorca-victoria-esperar-previa-analisis-pronostico-prediccion.html",
    "https://www.marca.com/futbol/europa-league/2025/09/24/betis-nottingham-forest-abran-paso-vuelve-eurobetis.html"
]

noticias = []

for url in urls:
    response = requests.get(url)
    if response.status_code != 200:
        continue
    soup = BeautifulSoup(response.text, "html.parser")

    # Si es la portada de fútbol
    if "futbol.html" in url:
        titulos = soup.find_all(class_="ue-c-cover-content__headline")
        for titulo_tag in titulos[:5]:  # Limitar a 5 titulares
            titulo = titulo_tag.get_text(strip=True)
            noticias.append({
                "titulo": titulo,
                "enlace": url,
                "fecha": "Desconocida",
                "autor": "Marca"
            })
    else:  # Artículos individuales
        header = soup.find("div", class_="ue-l-article__header")
        titulo = header.get_text(strip=True, separator=" ") if header else "Sin título"

        fecha_match = re.search(r"\d{4}/\d{2}/\d{2}", url)
        fecha = fecha_match.group().replace("/", "-") if fecha_match else "Desconocida"

        noticias.append({
            "titulo": titulo,
            "enlace": url,
            "fecha": fecha,
            "autor": "Marca"
        })

# Guardar en SQLite (solo las 5 noticias más recientes)
conn = sqlite3.connect("noticias.db")
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS noticias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        enlace TEXT,
        fecha TEXT,
        autor TEXT
    )
''')

# Borrar noticias antiguas
cursor.execute('DELETE FROM noticias')

# Insertar solo las 5 primeras noticias
for n in noticias[:5]:
    cursor.execute('''
        INSERT INTO noticias (titulo, enlace, fecha, autor)
        VALUES (?, ?, ?, ?)
    ''', (n["titulo"], n["enlace"], n["fecha"], n["autor"]))

conn.commit()
conn.close()

print(f"{len(noticias[:5])} noticias recientes guardadas en SQLite.")
