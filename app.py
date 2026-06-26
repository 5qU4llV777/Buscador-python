from flask import Flask, render_template_string, request
from bs4 import BeautifulSoup
import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# ──────────────────────────────────────────────
# Driver Selenium (headless Chrome)
# ──────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
]

def criar_driver():
    """Cria e retorna um WebDriver Chrome headless."""
    options = Options()
    options.add_argument("--headless=new")          # Chrome moderno
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--lang=pt-BR")
    # Desativa imagens para carregar mais rápido
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    # Se o chromedriver não estiver no PATH, informe o caminho:
    # service = Service(r"C:\caminho\para\chromedriver.exe")
    # driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    return driver

def get_html_selenium(url, wait_selector=None, wait_timeout=10):
    """
    Abre a URL com Selenium e retorna o HTML após renderização JS.
    wait_selector: CSS selector para aguardar antes de retornar (opcional).
    """
    driver = criar_driver()
    try:
        driver.get(url)
        if wait_selector:
            try:
                WebDriverWait(driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except Exception:
                pass  # Continua mesmo se o elemento não aparecer
        time.sleep(random.uniform(1.5, 3))
        return driver.page_source
    except Exception as e:
        print(f"[Selenium] Erro ao acessar {url}: {e}")
        return None
    finally:
        driver.quit()


# ──────────────────────────────────────────────
# Indeed
# ──────────────────────────────────────────────
def buscar_vagas_indeed(cargo, local):
    vagas = []
    cargo_fmt = cargo.replace(" ", "+")
    local_fmt = local.replace(" ", "+")
    url = f"https://br.indeed.com/jobs?q={cargo_fmt}&l={local_fmt}"
    html = get_html_selenium(url, wait_selector="div.job_seen_beacon")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="job_seen_beacon")
    for card in cards[:10]:
        titulo_tag = card.find("h2", class_="jobTitle")
        empresa_tag = card.find("span", attrs={"data-testid": "company-name"})
        link_tag = titulo_tag.find("a") if titulo_tag else None
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sem título"
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        link = "https://br.indeed.com" + link_tag["href"] if link_tag and link_tag.get("href") else "#"
        vagas.append({"titulo": titulo, "empresa": empresa, "link": link, "site": "Indeed"})
    return vagas


# ──────────────────────────────────────────────
# InfoJobs
# ──────────────────────────────────────────────
def buscar_vagas_infojobs(cargo, local):
    vagas = []
    cargo_fmt = cargo.replace(" ", "-").lower()
    local_fmt = local.replace(" ", "-").lower()
    url = f"https://www.infojobs.com.br/empregos-em-{local_fmt}/{cargo_fmt}.aspx"
    html = get_html_selenium(url, wait_selector="li.ij-BoxList-item")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("li", class_="ij-BoxList-item")
    for card in cards[:10]:
        titulo_tag = card.find("a", class_="ij-OfferList-item-title-link")
        empresa_tag = card.find("span", class_="ij-OfferList-item-company")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sem título"
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        link = titulo_tag["href"] if titulo_tag and titulo_tag.get("href") else "#"
        if link.startswith("/"):
            link = "https://www.infojobs.com.br" + link
        vagas.append({"titulo": titulo, "empresa": empresa, "link": link, "site": "InfoJobs"})
    return vagas


# ──────────────────────────────────────────────
# Catho
# ──────────────────────────────────────────────
def buscar_vagas_catho(cargo, local):
    vagas = []
    cargo_fmt = cargo.replace(" ", "%20")
    local_fmt = local.replace(" ", "%20")
    url = f"https://www.catho.com.br/vagas/{cargo_fmt}/{local_fmt}/"
    html = get_html_selenium(url, wait_selector="article")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("article")
    for card in cards[:10]:
        titulo_tag = card.find("h2")
        empresa_tag = card.find("span", class_=lambda c: c and "company" in c.lower())
        link_tag = card.find("a", href=True)
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sem título"
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        link = link_tag["href"] if link_tag else "#"
        if link.startswith("/"):
            link = "https://www.catho.com.br" + link
        vagas.append({"titulo": titulo, "empresa": empresa, "link": link, "site": "Catho"})
    return vagas


# ──────────────────────────────────────────────
# Vagas.com
# ──────────────────────────────────────────────
def buscar_vagas_vagas(cargo, local):
    vagas = []
    cargo_fmt = cargo.replace(" ", "-").lower()
    local_fmt = local.replace(" ", "-").lower()
    url = f"https://www.vagas.com.br/vagas-de-{cargo_fmt}-em-{local_fmt}"
    html = get_html_selenium(url, wait_selector="li.vaga")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("li", class_="vaga")
    for card in cards[:10]:
        titulo_tag = card.find("a", class_="link-detalhes-vaga")
        empresa_tag = card.find("span", class_="emprVaga")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sem título"
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        link = titulo_tag["href"] if titulo_tag and titulo_tag.get("href") else "#"
        if link.startswith("/"):
            link = "https://www.vagas.com.br" + link
        vagas.append({"titulo": titulo, "empresa": empresa, "link": link, "site": "Vagas.com"})
    return vagas


# ──────────────────────────────────────────────
# TrabalhaBrasil
# ──────────────────────────────────────────────
def buscar_vagas_trabalhabrasil(cargo, local):
    vagas = []
    cargo_fmt = cargo.replace(" ", "+")
    local_fmt = local.replace(" ", "+")
    url = f"https://www.trabalhabrasil.com.br/vagas-empregos-em-{local_fmt}/{cargo_fmt}"
    html = get_html_selenium(url, wait_selector="a.job-title")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("a", class_="job-title")
    empresas = soup.find_all("span", class_="company-name")
    for i, card in enumerate(cards[:10]):
        titulo = card.get_text(strip=True)
        empresa = empresas[i].get_text(strip=True) if i < len(empresas) else "Empresa não informada"
        link = card["href"] if card.get("href") else "#"
        if link.startswith("/"):
            link = "https://www.trabalhabrasil.com.br" + link
        vagas.append({"titulo": titulo, "empresa": empresa, "link": link, "site": "TrabalhaBrasil"})
    return vagas


# ──────────────────────────────────────────────
# Rota principal
# ──────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    vagas = []
    erro = None
    buscando = False

    if request.method == "POST":
        cargo = request.form.get("cargo", "").strip()
        local = request.form.get("local", "").strip()
        if not cargo:
            erro = "Por favor, informe o cargo desejado."
        else:
            buscando = True
            try:
                vagas.extend(buscar_vagas_indeed(cargo, local))
                vagas.extend(buscar_vagas_infojobs(cargo, local))
                vagas.extend(buscar_vagas_catho(cargo, local))
                vagas.extend(buscar_vagas_vagas(cargo, local))
                vagas.extend(buscar_vagas_trabalhabrasil(cargo, local))
            except Exception as e:
                erro = f"Erro durante a busca: {e}"

    return render_template_string("""
<!doctype html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Buscador de Vagas</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f0f2f5; }
        .hero { background: linear-gradient(135deg, #0d6efd, #0dcaf0); color: white; padding: 2.5rem 1rem; border-radius: 0 0 1rem 1rem; margin-bottom: 2rem; }
        .card { border: none; border-radius: 0.75rem; transition: transform .15s; }
        .card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.12) !important; }
        .badge-site { font-size: .75rem; }
    </style>
</head>
<body>
    <div class="hero text-center">
        <h1 class="fw-bold">🔍 Buscador de Vagas</h1>
        <p class="mb-3 opacity-75">Indeed · InfoJobs · Catho · Vagas.com · TrabalhaBrasil</p>
        <form method="post" class="row g-2 justify-content-center">
            <div class="col-md-4">
                <input type="text" name="cargo" class="form-control form-control-lg"
                       placeholder="Cargo (ex: Analista de Dados)" required
                       value="{{ request.form.get('cargo', '') }}">
            </div>
            <div class="col-md-3">
                <input type="text" name="local" class="form-control form-control-lg"
                       placeholder="Local (ex: São Paulo)"
                       value="{{ request.form.get('local', '') }}">
            </div>
            <div class="col-auto">
                <button type="submit" class="btn btn-light btn-lg fw-semibold px-4">Buscar</button>
            </div>
        </form>
    </div>

    <div class="container pb-5">
        {% if erro %}
            <div class="alert alert-danger">⚠️ {{ erro }}</div>
        {% endif %}

        {% if vagas %}
            <p class="text-muted mb-3">
                <strong>{{ vagas|length }}</strong> vaga(s) encontrada(s)
            </p>
            <div class="row g-3">
                {% for vaga in vagas %}
                <div class="col-md-6 col-lg-4">
                    <div class="card shadow-sm h-100">
                        <div class="card-body d-flex flex-column">
                            <h5 class="card-title mb-1">{{ vaga.titulo }}</h5>
                            <p class="text-muted small mb-2">🏢 {{ vaga.empresa }}</p>
                            <div class="mt-auto d-flex justify-content-between align-items-center">
                                <span class="badge bg-primary badge-site">{{ vaga.site }}</span>
                                <a href="{{ vaga.link }}" target="_blank"
                                   class="btn btn-sm btn-outline-primary">Ver vaga →</a>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>

        {% elif request.method == 'POST' and not erro %}
            <div class="alert alert-warning">
                Nenhuma vaga encontrada para os termos informados. Tente outros termos ou localidades.
            </div>
        {% endif %}
    </div>
</body>
</html>
    """, vagas=vagas, erro=erro)


if __name__ == "__main__":
    app.run(debug=True)