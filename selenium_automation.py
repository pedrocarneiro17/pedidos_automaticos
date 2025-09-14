import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# Função principal que executa a automação
def execute_mercos_automation(email, senha, lista_de_pedidos):
    LOGIN_URL = "https://app.mercos.com/login"

    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-cache")
    chrome_options.add_argument("--disk-cache-size=0")
    
    # Configurações obrigatórias para rodar em modo headless no Railway
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)

    # Lista para armazenar o log da execução, que será retornado para o Flask
    log_messages = []

    def log_and_print(message):
        log_messages.append(message)
        print(message)

    log_and_print("--- INICIANDO AUTOMAÇÃO GERAL DE PEDIDOS ---")

    try:
        # ETAPA DE LOGIN (AGORA RECEBE EMAIL E SENHA COMO PARÂMETROS)
        log_and_print(f"Acessando: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        log_and_print("Preenchendo formulário de login...")
        wait.until(EC.presence_of_element_located((By.ID, "id_usuario"))).send_keys(email)
        driver.find_element(By.ID, "id_senha").send_keys(senha)
        driver.find_element(By.ID, "botaoEfetuarLogin").click()
        log_and_print("Login enviado com sucesso! Aguardando o painel...")

        # GRANDE LOOP DE PEDIDOS
        total_pedidos = len(lista_de_pedidos)
        for i, dados_do_pedido_atual in enumerate(lista_de_pedidos):
            log_and_print(f"\n\n--- PROCESSANDO PEDIDO {i+1} de {total_pedidos} PARA O CLIENTE {dados_do_pedido_atual['cnpj_cliente']} ---")
            
            # Garante que estamos na tela de listagem de pedidos
            xpath_pedidos_menu = "//span[normalize-space()='Pedidos']"
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_pedidos_menu))).click()
            log_and_print("Na tela de listagem de Pedidos.")
            
            wait.until(EC.element_to_be_clickable((By.ID, "btn_criar_pedido"))).click()
            log_and_print("Acesso à tela de criação de pedido.")
            
            # Preenchimento do formulário
            campo_cliente = wait.until(EC.presence_of_element_located((By.ID, "id_codigo_cliente")))
            campo_cliente.send_keys(dados_do_pedido_atual["cnpj_cliente"])
            time.sleep(1.5); campo_cliente.send_keys(Keys.ENTER)
            log_and_print("Cliente inserido.")
            
            campo_representada = wait.until(EC.presence_of_element_located((By.ID, "id_codigo_representada")))
            campo_representada.send_keys(dados_do_pedido_atual["nome_representada"])
            time.sleep(1.5); campo_representada.send_keys(Keys.ENTER)
            log_and_print("Representada inserida.")

            # Loop de produtos para o pedido atual
            log_and_print("-> Iniciando adição de produtos...")
            for produto in dados_do_pedido_atual["produtos"]:
                campo_produto = wait.until(EC.presence_of_element_located((By.ID, "produto_autocomplete")))
                campo_produto.send_keys(produto['codigo']); time.sleep(2); campo_produto.send_keys(Keys.ENTER)
                
                campo_quantidade = wait.until(EC.visibility_of_element_located((By.ID, "id_quantidade")))
                campo_quantidade.send_keys(produto['quantidade']); time.sleep(2)
                
                campo_preco = wait.until(EC.visibility_of_element_located((By.ID, "id_preco_final")))
                campo_preco.clear(); campo_preco.send_keys(produto['preco']); time.sleep(2)
                
                botao_adicionar = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='botao medio primario' and normalize-space()='Adicionar']")))
                botao_adicionar.click()
                log_and_print(f"--> Produto '{produto['codigo']}' ADICIONADO.")
                time.sleep(1) # Pequena pausa para a página atualizar a lista de itens
            
            # Finalização do pedido atual
            botao_terminar = wait.until(EC.element_to_be_clickable((By.ID, "botao_terminei_de_adicionar")))
            botao_terminar.click()
            log_and_print("Processo de adição de itens finalizado.")
            
            campo_condicao = wait.until(EC.presence_of_element_located((By.ID, "id_condicao_pagamento")))
            campo_condicao.send_keys(dados_do_pedido_atual["condicao_pagamento"])
            time.sleep(1.5); campo_condicao.send_keys(Keys.ENTER)
            log_and_print("Condição de Pagamento confirmada.")
            
            time.sleep(2) # Pausa para a página processar antes de salvar detalhes
            botao_salvar = wait.until(EC.presence_of_element_located((By.ID, "botao-submit")))
            driver.execute_script("arguments[0].click();", botao_salvar)
            log_and_print("Detalhes do pedido salvos.")
            time.sleep(2) # Pausa para a página processar após salvar

            botao_gerar_pedido = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_gerar_pedido")))
            driver.execute_script("arguments[0].click();", botao_gerar_pedido)
            log_and_print(f"✅ PEDIDO {i+1} GERADO COM SUCESSO!")
            time.sleep(3) # Pausa para ver a tela de sucesso antes de voltar para o próximo pedido

        log_and_print("\n\n--- TODOS OS PEDIDOS FORAM PROCESSADOS ---")
        return {"status": "success", "log": log_messages}

    except Exception as e:
        error_message = f"❌ Ocorreu um erro durante a automação: {e}"
        log_and_print(error_message)
        return {"status": "error", "message": error_message, "log": log_messages}

    finally:
        log_and_print("Fechando o navegador.")
        driver.quit()