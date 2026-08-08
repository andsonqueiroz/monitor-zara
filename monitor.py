import asyncio
import re
import json
import smtplib
import os
from email.mime.text import MIMEText
from crawl4ai import AsyncWebCrawler

URL_ZARA = "https://www.zara.com/br/pt/sueter-de-trico-relaxed-fit-p04231416.html?v1=496052877&v2=2510635"
TAMANHO = "M"

EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE")
EMAIL_SENHA = os.environ.get("EMAIL_SENHA")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO")

async def check_zara():
    print("Iniciando Crawl4AI com magic=True...")
    
    # O crawler roda em modo stealth automático
    async with AsyncWebCrawler(verbose=True) as crawler:
        # A flag magic=True lida com pop-ups, anti-bots, mascara o IP e o user-agent
        result = await crawler.arun(url=URL_ZARA, magic=True)
        
        html = result.html
        if not html:
            print("Página bloqueada ou vazia.")
            return

        # 2. PROCURAR O ESTOQUE NO JSON
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

        # 3. CHECAR A VARIANTE
        estado_atual = "esgotado"
        variants = json_encontrado.get("hasVariant", [])
        
        for v in variants:
            if v.get("size") == TAMANHO:
                disp = v.get("offers", {}).get("availability", "")
                if "InStock" in disp or "LimitedAvailability" in disp:
                    estado_atual = "em_estoque"
                break

        print(f"Tamanho {TAMANHO}: {estado_atual}")

        # 4. CHECAR MEMÓRIA
        estado_anterior = "desconhecido"
        if os.path.exists("estado.txt"):
            with open("estado.txt", "r") as f:
                estado_anterior = f.read().strip()

        # 5. AVISAR E SALVAR
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
    # Roda a função assíncrona
    asyncio.run(check_zara())
