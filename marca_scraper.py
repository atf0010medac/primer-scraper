from bs4 import BeautifulSoup
import requests

urls = [
    "https://www.marca.com/futbol.html?intcmp=MENUPROD&s_kw=futbol",
    "https://www.marca.com/futbol/real-madrid/2025/09/24/madrid-llega-lanzado-derbi.html",
    "https://www.marca.com/futbol/primera-division/2025/09/24/atletico-rayo-vallecano-derbi-crucial-gran-derbi.html",
    "https://www.marca.com/futbol/primera-division/2025/09/23/getafe-alaves-mirar-abajo-previa-analisis-pronostico-prediccion.html",
    "https://www.marca.com/futbol/primera-division/2025/09/24/real-sociedad-mallorca-victoria-esperar-previa-analisis-pronostico-prediccion.html",
    "https://www.marca.com/futbol/europa-league/2025/09/24/betis-nottingham-forest-abran-paso-vuelve-eurobetis.html"
]

lista_titulares = []

for url in urls:
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        if "futbol.html" in url:
            titulos = soup.find_all(class_="ue-c-cover-content__headline")
            for titulo in titulos[:5]:
                texto = titulo.get_text(strip=True)
                lista_titulares.append(texto)
                print(texto)
                print()  
        else:
            header = soup.find("div", class_="ue-l-article__header")
            header_texto = header.get_text(strip=True, separator=" ") if header else "Sin título"

            cuerpo = soup.find("div", class_="ue-c-article__body")
            primer_parrafo = ""
            if cuerpo:
                parrafos = cuerpo.find_all("p")
                if parrafos:
                    primer_parrafo = parrafos[0].get_text(strip=True)

            print()
            print(header_texto)
            print(primer_parrafo)
            print("\n" + "-"*80 + "\n")

with open("titulares.html", "w", encoding="utf-8") as f:
    f.write("<!DOCTYPE html>\n")
    f.write("<html lang='es'>\n")
    f.write("<head>\n")
    f.write("    <meta charset='UTF-8'>\n")
    f.write("    <title>Titulares de Fútbol</title>\n")
    f.write("</head>\n")
    f.write("<body>\n")
    f.write("    <h1>Portada de Fútbol</h1>\n")

    for t in lista_titulares:
        f.write(f"    <h2>{t}</h2>\n")

    f.write("</body>\n")
    f.write("</html>\n")
