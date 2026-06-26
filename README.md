Como criar e ativar um ambiente virtual
Criar ambiente virtual  
No terminal, dentro da pasta do projeto:

``` python
python -m venv venv
```

Ativar ambiente virtual

Windows (PowerShell):
``` python
venv\Scripts\activate
```

Instalar dependências  
Dentro do ambiente, instale o que precisa:
``` python
pip install flask requests beautifulsoup4 python-dotenv
```
``` python
pip install selenium beautifulsoup4 flask
```
Salvar dependências  
Para registrar tudo em requirements.txt:
``` python
pip freeze > requirements.txt
```
Assim, qualquer pessoa pode recriar o mesmo ambiente com:
``` python
pip install -r requirements.txt
```

🔎 Como usar
Salve o código em app.py.

Execute com python app.py.

Abra no navegador: http://127.0.0.1:5000.

Digite cargo e localização → veja as vagas em tempo real.