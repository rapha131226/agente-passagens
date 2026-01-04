import base64
import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE PESQUISA (Junho/2026) ---
ORIGEM = "GRU"
DESTINO = "LHR"
JANELA_INICIO = datetime(2026, 6, 1)
JANELA_FIM = datetime(2026, 6, 10) # Pesquisa ida até dia 10
DURACAO_VIAGEM = 10 # Viagem de 10 dias exatos

# --- CREDENCIAIS ---
AMADEUS_KEY = os.getenv('AMADEUS_KEY')
AMADEUS_SECRET = os.getenv('AMADEUS_SECRET')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')

def obter_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    auth_data = f"{AMADEUS_KEY}:{AMADEUS_SECRET}"
    encoded_auth_data = base64.b64encode(auth_data.encode()).decode()
    headers = {"Authorization": f"Basic {encoded_auth_data}", "Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, headers=headers, data={"grant_type": "client_credentials"})
    if response.status_code != 200:
        print(f"ERRO AMADEUS: {response.text}")
        exit(1)
    return response.json()['access_token']

def buscar_passagens():
    token = obter_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    melhor_geral = None
    melhor_latam = None

    data_atual = JANELA_INICIO
    while data_atual <= JANELA_FIM:
        data_ida = data_atual.strftime('%Y-%m-%d')
        data_volta = (data_atual + timedelta(days=DURACAO_VIAGEM)).strftime('%Y-%m-%d')
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": ORIGEM, "destinationLocationCode": DESTINO,
            "departureDate": data_ida, "returnDate": data_volta,
            "adults": 2, "nonStop": "true", # Apenas voos diretos
            "currencyCode": "BRL", "max": 50
        }
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            offers = res.json().get('data', [])
            for offer in offers:
                preco = float(offer['price']['total'])
                cia = offer['validatingAirlineCodes'][0]
                
                # Lógica: Armazenar a melhor da LATAM e a melhor Geral
                if cia == 'LA' or cia == 'JJ': # LATAM Codes
                    if not melhor_latam or preco < float(melhor_latam['price']['total']):
                        melhor_latam = offer
                
                if not melhor_geral or preco < float(melhor_geral['price']['total']):
                    melhor_geral = offer
        
        data_atual += timedelta(days=1)
    return melhor_geral, melhor_latam

def formatar_voo(voo, titulo):
    if not voo: return f"--- {titulo} ---\nNenhum voo direto encontrado.\n\n"
    
    preco = voo['price']['total']
    cia = voo['validatingAirlineCodes'][0]
    data_ida = voo['itineraries'][0]['segments'][0]['departure']['at']
    data_volta = voo['itineraries'][1]['segments'][0]['departure']['at']
    
    # Criar link do Google Flights para facilitar a sua vida
    link = f"https://www.google.com/travel/flights?q=from:GRU;to:LHR;at:{data_ida[:10]};rt:{data_volta[:10]};nonstop:true"
    
    return f"""
--- {titulo} ---
Companhia: {cia}
Preço Total (2 pessoas): R$ {preco}
Datas: {data_ida[:10]} até {data_volta[:10]}
Link Google Flights: {link}
"""

def enviar_email(geral, latam):
    corpo = "✈️ RELATÓRIO DIÁRIO DE PASSAGENS - LONDRES JUNHO/2026\n\n"
    corpo += formatar_voo(latam, "OPÇÃO PREFERENCIAL LATAM")
    corpo += formatar_voo(geral, "OPÇÃO MAIS BARATA (GERAL)")
    
    msg = MIMEText(corpo)
    msg['Subject'] = f"✈️ Alerta: Londres Junho/2026 (10 dias)"
    msg['From'], msg['To'] = EMAIL_USER, EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())

if __name__ == "__main__":
    geral, latam = buscar_passagens()
    if geral or latam:
        enviar_email(geral, latam)
