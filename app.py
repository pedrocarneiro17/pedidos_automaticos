from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import threading
from selenium_automation import execute_mercos_automation
import os
import logging

# Configuração de logging para depuração
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"FLASK_SECRET_KEY: {os.getenv('FLASK_SECRET_KEY')}")
logger.debug(f"LOGIN_USERNAME: {os.getenv('LOGIN_USERNAME')}")
logger.debug(f"LOGIN_PASSWORD: {os.getenv('LOGIN_PASSWORD')}")

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'chave-secreta-muito-segura-e-dificil-de-adivinhar')

# Credenciais de login do ambiente
LOGIN_USERNAME = os.getenv('LOGIN_USERNAME', '').strip()
LOGIN_PASSWORD = os.getenv('LOGIN_PASSWORD', '').strip()

# --- Carregamento dos "Bancos de Dados" JSON ---
def load_data():
    try:
        with open('clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
        with open('products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
        return clients, products
    except FileNotFoundError:
        print("ERRO: Verifique se os arquivos 'clients.json' e 'products.json' estão na mesma pasta do app.py")
        return [], []

CLIENT_DATA, PRODUCT_DATA = load_data()

# --- Variáveis Globais ---
GLOBAL_EMAIL = ""
GLOBAL_SENHA = ""
GLOBAL_PEDIDOS_ACUMULADOS = []
AUTOMATION_RUNNING = False
AUTOMATION_LOG = []

# --- Middleware para verificar autenticação ---
def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__  # Preserva o nome da função para evitar erros do Flask
    return wrap

# --- Rota de Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        logger.debug(f"Form username: {username}, Form password: {password}")
        logger.debug(f"Expected LOGIN_USERNAME: {LOGIN_USERNAME}, LOGIN_PASSWORD: {LOGIN_PASSWORD}")
        if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Usuário ou senha inválidos.")
    return render_template('login.html', error=None)

# --- Rota de Logout ---
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('email', None)
    session.pop('senha', None)
    return redirect(url_for('login'))

# --- Novas Rotas de API ---
@app.route('/search_clients')
@login_required
def search_clients():
    query = request.args.get('query', '').lower()
    if not query:
        return jsonify([])
    
    matches = [
        client for client in CLIENT_DATA 
        if query in client['name'].lower() or query in client['cnpj']
    ]
    return jsonify(matches[:10]) # Retorna no máximo 10 resultados

@app.route('/get_products')
@login_required
def get_products():
    return jsonify(PRODUCT_DATA)

# --- Lógica da Automação (não muda) ---
def run_automation_in_background(email, senha, pedidos):
    global AUTOMATION_RUNNING, AUTOMATION_LOG, GLOBAL_PEDIDOS_ACUMULADOS
    AUTOMATION_RUNNING = True
    AUTOMATION_LOG = []
    
    result = execute_mercos_automation(email, senha, pedidos)
    AUTOMATION_LOG = result.get("log", ["Nenhum log disponível."])
    AUTOMATION_RUNNING = False
    
    if result.get("status") == "success":
        GLOBAL_PEDIDOS_ACUMULADOS.clear()
        
    print("Automação finalizada.")

# --- Rota Principal ---
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.values.get('action') == 'get_status':
        return jsonify({
            "running": AUTOMATION_RUNNING,
            "log": AUTOMATION_LOG,
            "current_orders": GLOBAL_PEDIDOS_ACUMULADOS
        })

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'set_credentials':
            global GLOBAL_EMAIL, GLOBAL_SENHA
            GLOBAL_EMAIL = request.form.get('email')
            GLOBAL_SENHA = request.form.get('senha')
            session['email'] = GLOBAL_EMAIL
            session['senha'] = GLOBAL_SENHA
            return jsonify({"status": "success", "message": "Credenciais salvas."})

        elif action == 'add_pedido':
            cnpj_cliente = request.form.get('cnpj_cliente')
            nome_representada = request.form.get('nome_representada')
            condicao_pagamento = request.form.get('condicao_pagamento')
            produtos_json = request.form.get('produtos_do_pedido', '[]')
            produtos = json.loads(produtos_json)

            if not produtos:
                return jsonify({"status": "error", "message": "Nenhum produto adicionado."}), 400

            novo_pedido = {
                "cnpj_cliente": cnpj_cliente, "nome_representada": nome_representada,
                "condicao_pagamento": condicao_pagamento, "produtos": produtos
            }
            GLOBAL_PEDIDOS_ACUMULADOS.append(novo_pedido)
            return jsonify({"status": "success", "message": "Pedido adicionado.", "current_orders": GLOBAL_PEDIDOS_ACUMULADOS})
            
        elif action == 'remove_pedido':
            index_to_remove = int(request.form.get('index'))
            if 0 <= index_to_remove < len(GLOBAL_PEDIDOS_ACUMULADOS):
                GLOBAL_PEDIDOS_ACUMULADOS.pop(index_to_remove)
                return jsonify({"status": "success", "message": "Pedido removido.", "current_orders": GLOBAL_PEDIDOS_ACUMULADOS})
            return jsonify({"status": "error", "message": "Índice inválido."}), 400
        
        elif action == 'remove_all_orders':
            GLOBAL_PEDIDOS_ACUMULADOS.clear()
            return jsonify({"status": "success", "message": "Fila limpa."})

        elif action == 'start_automation':
            if AUTOMATION_RUNNING:
                return jsonify({"status": "error", "message": "Automação já em execução."}), 400
            if not GLOBAL_EMAIL or not GLOBAL_SENHA:
                return jsonify({"status": "error", "message": "Credenciais não configuradas."}), 400
            if not GLOBAL_PEDIDOS_ACUMULADOS:
                return jsonify({"status": "error", "message": "Nenhum pedido para disparar."}), 400

            thread = threading.Thread(target=run_automation_in_background, 
                                      args=(GLOBAL_EMAIL, GLOBAL_SENHA, list(GLOBAL_PEDIDOS_ACUMULADOS)))
            thread.start()
            return jsonify({"status": "success", "message": "Automação iniciada."})

    return render_template('index.html', 
                           email=session.get('email', ''), 
                           senha=session.get('senha', ''),
                           current_orders=GLOBAL_PEDIDOS_ACUMULADOS)

if __name__ == '__main__':
    app.run(debug=True)