from flask import Flask, render_template_string, request
from bs4 import BeautifulSoup
import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

PALAVRAS_REMOTO = ["remoto", "remote", "home office", "homeoffice", "100% remoto"]

def is_remoto(texto):
    return any(p in texto.lower() for p in PALAVRAS_REMOTO)

# ──────────────────────────────────────────────
# Driver
# ──────────────────────────────────────────────
def criar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--lang=pt-BR")
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2
    })
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(25)
    return driver

def get_html_selenium(url, wait_selector=None, wait_timeout=12):
    driver = criar_driver()
    try:
        driver.get(url)
        if wait_selector:
            try:
                WebDriverWait(driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except Exception:
                pass
        time.sleep(random.uniform(2, 3.5))
        return driver.page_source
    except Exception as e:
        print(f"[Selenium] Erro: {url} → {e}")
        return None
    finally:
        driver.quit()


# ──────────────────────────────────────────────
# Indeed
# ──────────────────────────────────────────────
def buscar_vagas_indeed(cargo, modo, local=""):
    vagas = []
    cargo_fmt = cargo.replace(" ", "+")

    if modo == "remoto":
        url = (f"https://br.indeed.com/jobs?q={cargo_fmt}"
               f"&l=remoto&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11")
    else:
        local_fmt = local.replace(" ", "+")
        url = f"https://br.indeed.com/jobs?q={cargo_fmt}&l={local_fmt}"

    html = get_html_selenium(url, wait_selector="[data-testid='slider_item']", wait_timeout=15)
    if not html:
        return vagas

    soup = BeautifulSoup(html, "html.parser")

    # Indeed usa vários seletores dependendo do layout — tentamos todos
    cards = (
        soup.find_all("div", attrs={"data-testid": "slider_item"}) or
        soup.find_all("div", class_="job_seen_beacon") or
        soup.find_all("div", class_=lambda c: c and "jobCard" in c)
    )

    for card in cards[:10]:
        # Título — tenta múltiplos seletores
        titulo = (
            (card.find("span", attrs={"id": lambda i: i and i.startswith("jobTitle")}) or
             card.find("a", attrs={"data-testid": "job-title"}) or
             card.find("h2", class_=lambda c: c and "jobTitle" in c) or
             card.find("span", attrs={"title": True})
            )
        )
        titulo = titulo.get_text(strip=True) if titulo else None

        # Empresa
        empresa = (
            card.find("span", attrs={"data-testid": "company-name"}) or
            card.find("span", class_=lambda c: c and "companyName" in (c or ""))
        )
        empresa = empresa.get_text(strip=True) if empresa else "Empresa não informada"

        # Local
        local_tag = (
            card.find("div", attrs={"data-testid": "text-location"}) or
            card.find("div", class_=lambda c: c and "companyLocation" in (c or ""))
        )
        local_vaga = local_tag.get_text(strip=True) if local_tag else ("Remoto" if modo == "remoto" else local)

        # Link
        link_tag = card.find("a", href=True)
        link = ("https://br.indeed.com" + link_tag["href"]
                if link_tag and link_tag["href"].startswith("/") else
                link_tag["href"] if link_tag else "#")

        if titulo:
            vagas.append({"titulo": titulo, "empresa": empresa,
                          "local": local_vaga, "link": link, "site": "Indeed"})
    return vagas


# ──────────────────────────────────────────────
# LinkedIn
# ──────────────────────────────────────────────
def buscar_vagas_linkedin(cargo, modo, local=""):
    vagas = []
    cargo_fmt = cargo.replace(" ", "%20")

    if modo == "remoto":
        # f_WT=2 = remoto no LinkedIn
        url = (f"https://www.linkedin.com/jobs/search/?keywords={cargo_fmt}"
               f"&f_WT=2&location=Brasil&sortBy=DD")
    else:
        local_fmt = local.replace(" ", "%20")
        url = (f"https://www.linkedin.com/jobs/search/?keywords={cargo_fmt}"
               f"&location={local_fmt}&sortBy=DD")

    html = get_html_selenium(url, wait_selector=".base-card", wait_timeout=15)
    if not html:
        return vagas

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="base-card")

    for card in cards[:10]:
        titulo_tag = card.find("h3", class_=lambda c: c and "base-search-card__title" in c)
        empresa_tag = card.find("h4", class_=lambda c: c and "base-search-card__subtitle" in c)
        local_tag = card.find("span", class_=lambda c: c and "job-search-card__location" in c)
        link_tag = card.find("a", class_=lambda c: c and "base-card__full-link" in c)

        titulo = titulo_tag.get_text(strip=True) if titulo_tag else None
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        local_vaga = local_tag.get_text(strip=True) if local_tag else ("Remoto" if modo == "remoto" else local)
        link = link_tag["href"] if link_tag else "#"

        if titulo:
            vagas.append({"titulo": titulo, "empresa": empresa,
                          "local": local_vaga, "link": link, "site": "LinkedIn"})
    return vagas


# ──────────────────────────────────────────────
# InfoJobs
# ──────────────────────────────────────────────
def buscar_vagas_infojobs(cargo, modo, local=""):
    vagas = []
    cargo_fmt = cargo.replace(" ", "-").lower()

    if modo == "remoto":
        url = f"https://www.infojobs.com.br/empregos/{cargo_fmt}.aspx?teletrabalho=1"
    else:
        local_fmt = local.replace(" ", "-").lower()
        url = f"https://www.infojobs.com.br/empregos-em-{local_fmt}/{cargo_fmt}.aspx"

    html = get_html_selenium(url, wait_selector="li.ij-BoxList-item")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.find_all("li", class_="ij-BoxList-item")[:10]:
        titulo_tag = card.find("a", class_="ij-OfferList-item-title-link")
        empresa_tag = card.find("span", class_="ij-OfferList-item-company")
        local_tag = card.find("span", class_="ij-OfferList-item-location")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else None
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        local_vaga = local_tag.get_text(strip=True) if local_tag else ("Remoto" if modo == "remoto" else local)
        link = titulo_tag["href"] if titulo_tag else "#"
        if link.startswith("/"):
            link = "https://www.infojobs.com.br" + link
        if titulo:
            vagas.append({"titulo": titulo, "empresa": empresa,
                          "local": local_vaga, "link": link, "site": "InfoJobs"})
    return vagas


# ──────────────────────────────────────────────
# Catho
# ──────────────────────────────────────────────
def buscar_vagas_catho(cargo, modo, local=""):
    vagas = []
    cargo_fmt = cargo.replace(" ", "%20")

    if modo == "remoto":
        url = f"https://www.catho.com.br/vagas/{cargo_fmt}/home-office/"
    else:
        local_fmt = local.replace(" ", "%20")
        url = f"https://www.catho.com.br/vagas/{cargo_fmt}/{local_fmt}/"

    html = get_html_selenium(url, wait_selector="article")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.find_all("article")[:10]:
        titulo_tag = card.find("h2")
        empresa_tag = card.find("span", class_=lambda c: c and "company" in (c or "").lower())
        local_tag = card.find("span", class_=lambda c: c and "location" in (c or "").lower())
        link_tag = card.find("a", href=True)
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else None
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        local_vaga = local_tag.get_text(strip=True) if local_tag else ("Home Office" if modo == "remoto" else local)
        link = link_tag["href"] if link_tag else "#"
        if link.startswith("/"):
            link = "https://www.catho.com.br" + link
        if titulo:
            vagas.append({"titulo": titulo, "empresa": empresa,
                          "local": local_vaga, "link": link, "site": "Catho"})
    return vagas


# ──────────────────────────────────────────────
# Vagas.com
# ──────────────────────────────────────────────
def buscar_vagas_vagas(cargo, modo, local=""):
    vagas = []
    cargo_fmt = cargo.replace(" ", "-").lower()

    if modo == "remoto":
        url = f"https://www.vagas.com.br/vagas-de-{cargo_fmt}-home-office"
    else:
        local_fmt = local.replace(" ", "-").lower()
        url = f"https://www.vagas.com.br/vagas-de-{cargo_fmt}-em-{local_fmt}"

    html = get_html_selenium(url, wait_selector="li.vaga")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.find_all("li", class_="vaga")[:10]:
        titulo_tag = card.find("a", class_="link-detalhes-vaga")
        empresa_tag = card.find("span", class_="emprVaga")
        local_tag = card.find("span", class_="cidade")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else None
        empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
        local_vaga = local_tag.get_text(strip=True) if local_tag else ("Home Office" if modo == "remoto" else local)
        link = titulo_tag["href"] if titulo_tag else "#"
        if link.startswith("/"):
            link = "https://www.vagas.com.br" + link
        if titulo:
            vagas.append({"titulo": titulo, "empresa": empresa,
                          "local": local_vaga, "link": link, "site": "Vagas.com"})
    return vagas


# ──────────────────────────────────────────────
# TrabalhaBrasil
# ──────────────────────────────────────────────
def buscar_vagas_trabalhabrasil(cargo, modo, local=""):
    vagas = []
    sufixo = " remoto" if modo == "remoto" else f" {local}"
    cargo_fmt = (cargo + sufixo).replace(" ", "+")
    url = f"https://www.trabalhabrasil.com.br/vagas-empregos/{cargo_fmt}"

    html = get_html_selenium(url, wait_selector="a.job-title")
    if not html:
        return vagas
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("a", class_="job-title")
    empresas = soup.find_all("span", class_="company-name")
    locais = soup.find_all("span", class_="job-location")
    for i, card in enumerate(cards[:10]):
        titulo = card.get_text(strip=True)
        empresa = empresas[i].get_text(strip=True) if i < len(empresas) else "Empresa não informada"
        local_vaga = locais[i].get_text(strip=True) if i < len(locais) else ("Remoto" if modo == "remoto" else local)
        link = card.get("href", "#")
        if link.startswith("/"):
            link = "https://www.trabalhabrasil.com.br" + link
        if modo == "remoto" and not is_remoto(titulo + local_vaga):
            continue
        vagas.append({"titulo": titulo, "empresa": empresa,
                      "local": local_vaga, "link": link, "site": "TrabalhaBrasil"})
    return vagas


# Cores por site
SITE_CORES = {
    "Indeed":        ("0d6efd", "LinkedIn Jobs"),
    "LinkedIn":      ("0a66c2", "LinkedIn"),
    "InfoJobs":      ("ff6600", "InfoJobs"),
    "Catho":         ("e30613", "Catho"),
    "Vagas.com":     ("00a859", "Vagas.com"),
    "TrabalhaBrasil":("6f42c1", "TrabalhaBrasil"),
}

# ──────────────────────────────────────────────
# Rota principal
# ──────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    vagas = []
    erro = None
    cargo_val = ""
    local_val = ""
    modo_val = "remoto"

    if request.method == "POST":
        cargo_val = request.form.get("cargo", "").strip()
        local_val = request.form.get("local", "").strip()
        modo_val  = request.form.get("modo", "remoto")

        if not cargo_val:
            erro = "Por favor, informe o cargo desejado."
        else:
            try:
                vagas.extend(buscar_vagas_indeed(cargo_val, modo_val, local_val))
                vagas.extend(buscar_vagas_linkedin(cargo_val, modo_val, local_val))
                vagas.extend(buscar_vagas_infojobs(cargo_val, modo_val, local_val))
                vagas.extend(buscar_vagas_catho(cargo_val, modo_val, local_val))
                vagas.extend(buscar_vagas_vagas(cargo_val, modo_val, local_val))
                vagas.extend(buscar_vagas_trabalhabrasil(cargo_val, modo_val, local_val))
            except Exception as e:
                erro = f"Erro durante a busca: {e}"

    SITE_CORES_JSON = str(SITE_CORES).replace("'", '"')

    return render_template_string(r"""
<!doctype html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Buscador de Vagas</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root { --grad-a: #0d6efd; --grad-b: #0dcaf0; }
        body { background: #f0f2f5; }

        .hero {
            background: linear-gradient(135deg, var(--grad-a), var(--grad-b));
            color: #fff;
            padding: 2.5rem 1rem 3.5rem;
            border-radius: 0 0 1.5rem 1.5rem;
            margin-bottom: 2rem;
        }

        /* Toggle remoto / local */
        .modo-toggle { display:inline-flex; background:rgba(255,255,255,.2); border-radius:99px; padding:4px; }
        .modo-toggle input { display:none; }
        .modo-toggle label {
            cursor:pointer; padding:.4rem 1.2rem; border-radius:99px;
            font-weight:600; font-size:.9rem; color:rgba(255,255,255,.75);
            transition: all .2s;
        }
        .modo-toggle input:checked + label {
            background:#fff; color:#0d6efd;
        }

        /* Campo local — aparece só no modo "local" */
        #local-field { transition: opacity .3s, max-height .3s; overflow:hidden; max-height:60px; }
        #local-field.hidden { opacity:0; max-height:0; pointer-events:none; }

        /* Cards */
        .card { border:none; border-radius:.75rem; transition:transform .15s; }
        .card:hover { transform:translateY(-3px); box-shadow:0 6px 20px rgba(0,0,0,.13)!important; }
        .card-site-bar { height:4px; border-radius:.75rem .75rem 0 0; }

        /* Loading overlay */
        #loading {
            display:none; position:fixed; inset:0;
            background:rgba(0,0,0,.55); z-index:9999;
            flex-direction:column; align-items:center; justify-content:center; color:#fff;
        }
        #loading.show { display:flex; }
        .spinner-ring {
            width:64px; height:64px; border:6px solid rgba(255,255,255,.3);
            border-top-color:#fff; border-radius:50%;
            animation: spin 1s linear infinite; margin-bottom:1rem;
        }
        @keyframes spin { to { transform:rotate(360deg); } }
        #timer { font-size:1.1rem; opacity:.85; }

        /* Filtros de site */
        .filter-btn { border-radius:99px; font-size:.8rem; padding:.25rem .85rem; }
        .filter-btn.active { color:#fff; }
    </style>
</head>
<body>

<!-- Loading overlay -->
<div id="loading">
    <div class="spinner-ring"></div>
    <div>Buscando vagas em todos os sites…</div>
    <div id="timer">⏱ 0s</div>
    <small class="mt-2 opacity-50">Pode levar até 60 segundos</small>
</div>

<div class="hero text-center">
    <h1 class="fw-bold mb-1">💼 Buscador de Vagas</h1>
    <p class="opacity-75 mb-3">Indeed · LinkedIn · InfoJobs · Catho · Vagas.com · TrabalhaBrasil</p>

    <form method="post" id="searchForm" class="d-flex flex-column align-items-center gap-3">

        <!-- Toggle Remoto / Local -->
        <div class="modo-toggle">
            <input type="radio" name="modo" id="modo-remoto" value="remoto"
                   {% if modo_val == 'remoto' %}checked{% endif %}>
            <label for="modo-remoto">🌐 Remoto</label>

            <input type="radio" name="modo" id="modo-local" value="local"
                   {% if modo_val == 'local' %}checked{% endif %}>
            <label for="modo-local">📍 Presencial</label>
        </div>

        <div class="d-flex flex-wrap gap-2 justify-content-center w-100">
            <input type="text" name="cargo" id="cargo"
                   class="form-control form-control-lg" style="max-width:380px"
                   placeholder="Cargo (ex: Desenvolvedor Python)"
                   value="{{ cargo_val }}" required>

            <div id="local-field" class="{% if modo_val == 'remoto' %}hidden{% endif %}">
                <input type="text" name="local" id="local"
                       class="form-control form-control-lg" style="max-width:220px"
                       placeholder="Cidade / Estado"
                       value="{{ local_val }}">
            </div>

            <button type="submit" class="btn btn-light btn-lg fw-semibold px-4">
                🔍 Buscar
            </button>
        </div>
    </form>
</div>

<div class="container pb-5">
    {% if erro %}
        <div class="alert alert-danger">⚠️ {{ erro }}</div>
    {% endif %}

    {% if vagas %}
        <!-- Filtros por site -->
        <div class="d-flex flex-wrap gap-2 mb-3 align-items-center">
            <span class="text-muted me-1"><strong>{{ vagas|length }}</strong> vaga(s) · Filtrar:</span>
            <button class="btn btn-outline-secondary filter-btn active" data-site="todos">Todos</button>
            {% set sites = [] %}
            {% for v in vagas %}{% if v.site not in sites %}{% set _ = sites.append(v.site) %}{% endif %}{% endfor %}
            {% for site in sites %}
                <button class="btn btn-outline-secondary filter-btn" data-site="{{ site }}">{{ site }}</button>
            {% endfor %}
        </div>

        <div class="row g-3" id="vagasGrid">
            {% for vaga in vagas %}
            {% set cor = {'Indeed':'0d6efd','LinkedIn':'0a66c2','InfoJobs':'ff6600','Catho':'e30613','Vagas.com':'00a859','TrabalhaBrasil':'6f42c1'} %}
            {% set c = cor.get(vaga.site, '555555') %}
            <div class="col-md-6 col-lg-4 vaga-item" data-site="{{ vaga.site }}">
                <div class="card shadow-sm h-100">
                    <div class="card-site-bar" style="background:#{{ c }}"></div>
                    <div class="card-body d-flex flex-column">
                        <h5 class="card-title mb-1" style="font-size:1rem">{{ vaga.titulo }}</h5>
                        <p class="text-muted small mb-1">🏢 {{ vaga.empresa }}</p>
                        <p class="small mb-3">📍 <span class="badge rounded-pill text-bg-light border">{{ vaga.local }}</span></p>
                        <div class="mt-auto d-flex justify-content-between align-items-center">
                            <span class="badge rounded-pill" style="background:#{{ c }}">{{ vaga.site }}</span>
                            <a href="{{ vaga.link }}" target="_blank"
                               class="btn btn-sm btn-outline-secondary">Ver vaga →</a>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

    {% elif request.method == 'POST' and not erro %}
        <div class="alert alert-warning">
            Nenhuma vaga encontrada para "<strong>{{ cargo_val }}</strong>". Tente outros termos.
        </div>
    {% endif %}
</div>

<script>
// ── Toggle remoto/local ──
const modoRemoto = document.getElementById('modo-remoto');
const modoLocal  = document.getElementById('modo-local');
const localField = document.getElementById('local-field');
const localInput = document.getElementById('local');

function atualizarModo() {
    if (modoLocal.checked) {
        localField.classList.remove('hidden');
        localInput.required = true;
    } else {
        localField.classList.add('hidden');
        localInput.required = false;
        localInput.value = '';
    }
}
modoRemoto.addEventListener('change', atualizarModo);
modoLocal.addEventListener('change', atualizarModo);
atualizarModo();

// ── Loading com timer ──
const form = document.getElementById('searchForm');
const loading = document.getElementById('loading');
const timerEl = document.getElementById('timer');

form.addEventListener('submit', () => {
    loading.classList.add('show');
    let s = 0;
    setInterval(() => { s++; timerEl.textContent = `⏱ ${s}s`; }, 1000);
});

// ── Filtro por site ──
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active', 'text-white'));
        btn.classList.add('active');
        const site = btn.dataset.site;
        document.querySelectorAll('.vaga-item').forEach(item => {
            item.style.display = (site === 'todos' || item.dataset.site === site) ? '' : 'none';
        });
    });
});
</script>
</body>
</html>
    """, vagas=vagas, erro=erro, cargo_val=cargo_val, local_val=local_val, modo_val=modo_val)


if __name__ == "__main__":
    app.run(debug=True)