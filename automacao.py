import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# --- DADOS DOS PEDIDOS (MODIFIQUE AQUI PARA CRIAR VÁRIOS PEDIDOS) ---
LOGIN_URL = "https://app.mercos.com/login"
EMAIL = "pedrocarneiro1703@gmail.com"
SENHA = "347347aaA"

# LISTA PRINCIPAL DE PEDIDOS - Adicione quantos dicionários de pedido quiser aqui
LISTA_DE_PEDIDOS = [
    # Pedido 1
    {
        "cnpj_cliente": "02.814.497/0001-07",
        "nome_representada": "Empresa de Pedro Carneiro",
        "condicao_pagamento": "pix",
        "produtos": [
            {'codigo': '100', 'quantidade': '15', 'preco': '25,50'},
            {'codigo': '101', 'quantidade': '10', 'preco': '12,99'}
        ]
    },
    # Pedido 2
    {
        "cnpj_cliente": "17.256.512/0001-16", # CNPJ de outro cliente
        "nome_representada": "Empresa de Pedro Carneiro",
        "condicao_pagamento": "A vista",
        "produtos": [
            {'codigo': '102', 'quantidade': '50', 'preco': '145,00'}
        ]
    }
    # Adicione o Pedido 3, 4, etc. aqui...
]

# --- CONFIGURAÇÃO ---
chrome_options = Options()
# ... (demais configurações permanecem as mesmas)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-cache")
chrome_options.add_argument("--disk-cache-size=0")

service = ChromeService(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 20)

print("--- INICIANDO AUTOMAÇÃO GERAL DE PEDIDOS ---")

try:
    # ETAPA DE LOGIN (FEITA APENAS UMA VEZ)
    print(f"Acessando: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    print("Preenchendo formulário de login...")
    wait.until(EC.presence_of_element_located((By.ID, "id_usuario"))).send_keys(EMAIL)
    driver.find_element(By.ID, "id_senha").send_keys(SENHA)
    driver.find_element(By.ID, "botaoEfetuarLogin").click()
    print("Login enviado com sucesso!")

    # GRANDE LOOP DE PEDIDOS
    total_pedidos = len(LISTA_DE_PEDIDOS)
    for i, dados_do_pedido_atual in enumerate(LISTA_DE_PEDIDOS):
        print(f"\n\n--- PROCESSANDO PEDIDO {i+1} de {total_pedidos} PARA O CLIENTE {dados_do_pedido_atual['cnpj_cliente']} ---")
        
        # Garante que estamos na tela de listagem de pedidos
        xpath_pedidos_menu = "//span[normalize-space()='Pedidos']"
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath_pedidos_menu))).click()
        print("Na tela de listagem de Pedidos.")
        
        wait.until(EC.element_to_be_clickable((By.ID, "btn_criar_pedido"))).click()
        print("Acesso à tela de criação de pedido.")
        
        # Preenchimento do formulário
        campo_cliente = wait.until(EC.presence_of_element_located((By.ID, "id_codigo_cliente")))
        campo_cliente.send_keys(dados_do_pedido_atual["cnpj_cliente"])
        time.sleep(1.5); campo_cliente.send_keys(Keys.ENTER)
        print("Cliente inserido.")
        
        campo_representada = wait.until(EC.presence_of_element_located((By.ID, "id_codigo_representada")))
        campo_representada.send_keys(dados_do_pedido_atual["nome_representada"])
        time.sleep(1.5); campo_representada.send_keys(Keys.ENTER)
        print("Representada inserida.")

        # Loop de produtos para o pedido atual
        print("-> Iniciando adição de produtos...")
        for produto in dados_do_pedido_atual["produtos"]:
            campo_produto = wait.until(EC.presence_of_element_located((By.ID, "produto_autocomplete")))
            campo_produto.send_keys(produto['codigo']); time.sleep(2); campo_produto.send_keys(Keys.ENTER)
            
            campo_quantidade = wait.until(EC.visibility_of_element_located((By.ID, "id_quantidade")))
            campo_quantidade.send_keys(produto['quantidade']); time.sleep(2)
            
            campo_preco = wait.until(EC.visibility_of_element_located((By.ID, "id_preco_final")))
            campo_preco.clear(); campo_preco.send_keys(produto['preco']); time.sleep(2)
            
            botao_adicionar = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='botao medio primario' and normalize-space()='Adicionar']")))
            botao_adicionar.click()
            print(f"--> Produto '{produto['codigo']}' ADICIONADO.")
            time.sleep(1)
        
        # Finalização do pedido atual
        botao_terminar = wait.until(EC.element_to_be_clickable((By.ID, "botao_terminei_de_adicionar")))
        botao_terminar.click()
        
        campo_condicao = wait.until(EC.presence_of_element_located((By.ID, "id_condicao_pagamento")))
        campo_condicao.send_keys(dados_do_pedido_atual["condicao_pagamento"])
        time.sleep(1.5); campo_condicao.send_keys(Keys.ENTER)
        print("Condição de Pagamento confirmada.")
        
        time.sleep(2)
        botao_salvar = wait.until(EC.presence_of_element_located((By.ID, "botao-submit")))
        driver.execute_script("arguments[0].click();", botao_salvar)
        print("Detalhes do pedido salvos.")
        time.sleep(2)
        
        botao_gerar_pedido = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_gerar_pedido")))
        driver.execute_script("arguments[0].click();", botao_gerar_pedido)
        print(f"✅ PEDIDO {i+1} GERADO COM SUCESSO!")
        time.sleep(3) # Pausa para ver a tela de sucesso antes de voltar

    print("\n\n--- TODOS OS PEDIDOS FORAM PROCESSADOS ---")
    time.sleep(5)

except Exception as e:
    print(f"❌ Ocorreu um erro durante a automação: {e}")
    driver.save_screenshot("erro_screenshot.png")
    print("Um screenshot do erro foi salvo como 'erro_screenshot.png'")
    time.sleep(10)

finally:
    print("Fechando o navegador.")
    driver.quit()

print("--- FIM DA AUTOMAÇÃO GERAL DE PEDIDOS ---")