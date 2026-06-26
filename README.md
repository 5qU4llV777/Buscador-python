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
Salvar dependências  
Para registrar tudo em requirements.txt:
``` python
pip freeze > requirements.txt
```
Assim, qualquer pessoa pode recriar o mesmo ambiente com:
``` python
pip install -r requirements.txt
```