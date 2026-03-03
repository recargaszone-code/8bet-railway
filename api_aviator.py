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
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# ========================= CONFIG =========================
TELEGRAM_TOKEN = "8742776802:AAHSzD1qTwCqMEOdoW9_pT2l5GfmMBWUZQY"
TELEGRAM_CHAT_ID = "7427648935"
LOGIN = "857789345"
PASSWORD = "killobytes"
URL = "https://m.888bets.co.mz/pt/games/detail/jogos/normal/7787"

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

# ========================= SCRAPER SEM PROXY + PRINTS EM CADA PASSO =========================
def iniciar_scraper():
    global historico
    while True:
        driver = None
        try:
            enviar_telegram("🟢 Iniciando scraper 888bets (sem proxy, com prints)...")

            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=414,896")  # tamanho mobile pra stealth
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            wait = WebDriverWait(driver, 70)

            # PASSO 1 - Abrir página
            driver.get(URL)
            enviar_telegram("🌐 1. Página aberta")
            enviar_print(driver, "📸 1. Página carregada")
            time.sleep(25)

            # PASSO 2 - Login
            try:
                enviar_telegram("🔑 2. Tentando login...")
                enviar_print(driver, "📸 2. Antes do login")

                phone = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-test="sign-in-modal-phone-input"]')))
                phone.clear()
                phone.send_keys(LOGIN)
                enviar_telegram("📌 3. Telefone preenchido")
                enviar_print(driver, "📸 3. Telefone preenchido")
                time.sleep(15)

                pwd = driver.find_element(By.ID, "login-password")
                pwd.clear()
                pwd.send_keys(PASSWORD)
                enviar_telegram("📌 4. Senha preenchida")
                enviar_print(driver, "📸 4. Senha preenchida")
                time.sleep(15)

                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="sign-in-modal-btn"]')))
                btn.click()
                enviar_telegram("✅ 5. Login enviado!")
                enviar_print(driver, "📸 5. Login enviado")
                time.sleep(25)
            except Exception as e:
                enviar_telegram(f"⚠️ 5. Login pulado ou erro: {str(e)}")
                enviar_print(driver, "📸 5. Login pulado")

            # PASSO 6 - IFRAME
            try:
                iframe = wait.until(EC.presence_of_element_located((By.ID, "gm-frm")))
                driver.switch_to.frame(iframe)
                enviar_telegram("✅ 6. Entrou no iframe gm-frm")
                enviar_print(driver, "📸 6. Dentro do iframe")
            except:
                enviar_telegram("❌ 6. Iframe não encontrado")
            time.sleep(20)

            enviar_telegram("🚀 7. Monitoramento iniciado (a cada 25s)")
            enviar_print(driver, "📸 7. Monitoramento iniciado")

            # LOOP HISTÓRICO
            while True:
                try:
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
                        msg = f"""*📊 Histórico Atualizado – 888bets*

[{lista_str}]

Total: **{len(historico)}** | Último: **{historico[-1]:.2f}x**"""
                        enviar_telegram(msg)
                        enviar_print(driver, "📸 Histórico atualizado")

                except Exception as e:
                    enviar_telegram(f"🔥 Erro no loop: {type(e).__name__} → tentando novamente")
                
                time.sleep(25)

        except Exception as e:
            enviar_telegram(f"🔥 ERRO CRÍTICO: {type(e).__name__} → reiniciando em 20s")
            time.sleep(20)
        finally:
            try:
                if driver:
                    driver.quit()
            except:
                pass

# ========================= API =========================
@app.route("/api/history")
def get_history(): return jsonify(historico)
@app.route("/api/last")
def get_last(): return jsonify(historico[-1] if historico else None)
@app.route("/")
def home(): return "✅ 888bets Aviator rodando sem proxy!"

if __name__ == "__main__":
    threading.Thread(target=iniciar_scraper, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
