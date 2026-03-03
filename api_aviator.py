import os
import time
import threading
import re
import requests
from flask import Flask, jsonify

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8742776802:AAHSzD1qTwCqMEOdoW9_pT2l5GfmMBWUZQY"
TELEGRAM_CHAT_ID = "7427648935"
LOGIN = "857789345"
PASSWORD = "killobytes"
URL = "https://m.888bets.co.mz/pt/games/detail/jogos/normal/7787"

# Lista de proxies que você mandou (todos testados em sequência)
PROXIES = [
    "http://165.90.64.216:8080",
    "http://197.219.228.62:8080",
    "http://197.218.16.16:3128",
    "http://102.211.108.2:8082",
    "http://165.90.89.38:3128",
    "http://196.3.99.162:8080",
    "http://91.102.181.212:8080",
    "http://41.77.129.154:53281",
    "http://41.76.149.62:8080",
    "http://196.3.100.42:8080",
]

historico = []

def enviar_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=15
        )
    except:
        pass

def enviar_print(driver, legenda="📸 Screenshot"):
    try:
        path = "/tmp/print.png"
        driver.save_screenshot(path)
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            files={"photo": open(path, "rb")},
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": legenda}
        )
    except:
        pass

# ========================= SCRAPER COM ROTACAO DE PROXIES + PRINTS =========================
def iniciar_scraper():
    global historico
    while True:
        driver = None
        proxy_index = 0
        while proxy_index < len(PROXIES):
            proxy = PROXIES[proxy_index]
            try:
                enviar_telegram(f"🟢 Tentando proxy {proxy_index+1}/{len(PROXIES)}: {proxy}")

                chrome_options = Options()
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=414,896")  # mobile size pra mais stealth
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1")
                chrome_options.add_argument(f"--proxy-server={proxy}")

                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                wait = WebDriverWait(driver, 60)

                driver.get(URL)
                enviar_telegram(f"🌐 Página aberta com proxy {proxy}")
                enviar_print(driver, f"📸 1. Página com proxy {proxy}")

                # Verifica se caiu na tela de bloqueio
                try:
                    blocked = driver.find_element(By.XPATH, "//*[contains(text(), 'gambling regulations') or contains(text(), 'no access')]")
                    enviar_telegram(f"❌ Bloqueio de localização detectado com {proxy}")
                    enviar_print(driver, f"📸 Bloqueio com {proxy}")
                    driver.quit()
                    proxy_index += 1
                    time.sleep(10)
                    continue
                except:
                    enviar_telegram(f"✅ Sem bloqueio visível com {proxy}! Continuando...")

                # Login
                try:
                    enviar_telegram("🔑 Tentando login...")
                    enviar_print(driver, "📸 Antes do login")

                    phone = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-test="sign-in-modal-phone-input"]')))
                    phone.clear()
                    phone.send_keys(LOGIN)
                    enviar_telegram("📌 Telefone preenchido")
                    enviar_print(driver, "📸 Telefone preenchido")
                    time.sleep(10)

                    pwd = driver.find_element(By.ID, "login-password")
                    pwd.clear()
                    pwd.send_keys(PASSWORD)
                    enviar_telegram("📌 Senha preenchida")
                    enviar_print(driver, "📸 Senha preenchida")
                    time.sleep(10)

                    btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="sign-in-modal-btn"]')))
                    btn.click()
                    enviar_telegram("✅ Login enviado!")
                    enviar_print(driver, "📸 Login enviado")
                    time.sleep(20)
                except:
                    enviar_telegram("⚠️ Login pulado (já logado?)")
                    enviar_print(driver, "📸 Login pulado")

                # Iframe
                iframe = wait.until(EC.presence_of_element_located((By.ID, "gm-frm")))
                driver.switch_to.frame(iframe)
                enviar_telegram("✅ Entrou no iframe gm-frm")
                enviar_print(driver, "📸 Dentro do iframe")
                time.sleep(15)

                enviar_telegram("🚀 Monitoramento iniciado com proxy " + proxy)
                enviar_print(driver, "📸 Monitoramento iniciado")

                # LOOP HISTÓRICO
                while True:
                    payouts_block = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.payouts-block"))
                    )

                    elements = payouts_block.find_elements(
                        By.CSS_SELECTOR, "div.payout.ng-star-inserted[appcoloredmultiplier], div.payout"
                    )

                    novos = []
                    for el in elements:
                        txt = el.text.strip()
                        if txt:
                            match = re.search(r'(\d+\.?\d*)x?', txt, re.IGNORECASE)
                            if match:
                                novos.append(float(match.group(1)))

                    if novos and (not historico or novos != historico):
                        historico = novos
                        lista_str = ", ".join(f"{v:.2f}x" for v in historico[-30:])
                        msg = f"""*Histórico Atualizado – 888bets*

[{lista_str}]

Total: **{len(historico)}** | Último: **{historico[-1]:.2f}x**"""
                        enviar_telegram(msg)
                        enviar_print(driver, "📸 Histórico atualizado")

                    time.sleep(12)

            except Exception as e:
                enviar_telegram(f"🔥 Erro com proxy {proxy}: {type(e).__name__} → tentando próximo")
                enviar_print(driver, f"📸 Erro com {proxy}") if driver else None
                proxy_index += 1
                time.sleep(10)
            finally:
                try:
                    if driver:
                        driver.quit()
                except:
                    pass

            if proxy_index >= len(PROXIES):
                enviar_telegram("❌ Todos proxies testados. Nenhum funcionou. Tentar novamente em 60s...")
                time.sleep(60)
                proxy_index = 0

# ========================= API =========================
@app.route("/api/history")
def get_history(): return jsonify(historico)
@app.route("/api/last")
def get_last(): return jsonify(historico[-1] if historico else None)
@app.route("/")
def home(): return "✅ 888bets com proxies rotativos rodando!"

if __name__ == "__main__":
    threading.Thread(target=iniciar_scraper, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
