from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import re
import json
import smtplib
import os
from email.mime.text import MIMEText
import time

URL_ZARA = "https://www.zara.com/br/pt/sueter-de-trico-relaxed-fit-p04231416.html?v1=496052877&v2=2510635"
TAMANHO = "M"

EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE")
EMAIL_SENHA = os.environ.get("EMAIL_SENHA")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO")

def main():
    # 1. ACESSO INVISÍVEL (COM MODO STEALTH ATIVADO)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Colocamos um tamanho de tela padrão de PC para parecer mais real
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        # INJETA A INVISIBILIDADE PARA ENGANAR A AKAMAI
        stealth_sync(page) 
        
        # Espera até que todo o tráfego de rede pare (garante que o JS carregou)
        page.goto(URL_ZARA, wait_until="networkidle") 
        time.sleep(3) # Aguarda 3 segundos extras como um humano faria
        
        html = page.content()
        browser.close()

    pattern = r'<script[^>]*type="application/ld\+json"[^>]*>([\s\S]*?)</script>'
    matches = re.findall(pattern, html, re.IGNORECASE)
    
    json_encontrado = None
    for match in matches:
        try:
            dados = json.loads(match)
            if dados.get("@type") == "ProductGroup":
                json_encontrado = dados
                break
        except:
            continue

    if not json_encontrado:
        print("Página bloqueada ou mudou de estrutura.")
        return

    estado_atual = "esgotado"
    variants = json_encontrado.get("hasVariant", [])
    
    for v in variants:
        if v.get("size") == TAMANHO:
            disp = v.get("offers", {}).get("availability", "")
            if "InStock" in disp or "LimitedAvailability" in disp:
                estado_atual = "em_estoque"
            break

    print(f"Tamanho {TAMANHO}: {estado_atual}")

    estado_anterior = "desconhecido"
    if os.path.exists("estado.txt"):
        with open("estado.txt", "r") as f:
            estado_anterior = f.read().strip()

    if estado_atual == "em_estoque" and estado_anterior != "em_estoque":
        msg = MIMEText(f"O suéter voltou ao estoque! Compre agora:\n\n{URL_ZARA}")
        msg['Subject'] = f"🚨 ZARA: Suéter Tamanho {TAMANHO} DISPONÍVEL!"
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINO

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(EMAIL_REMETENTE, EMAIL_SENHA)
            server.send_message(msg)
            server.quit()
            print("E-mail enviado com sucesso!")
        except Exception as e:
            print(f"Erro ao enviar email: {e}")

    with open("estado.txt", "w") as f:
        f.write(estado_atual)

if __name__ == "__main__":
    main()
