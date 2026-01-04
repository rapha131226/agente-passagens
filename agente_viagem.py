import base64
import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE PESQUISA (Junho/2026) ---
ORIGEM, DESTINO = "GRU", "LHR"
JANELA_INICIO = datetime(2026, 6, 1)
JANELA_FIM = datetime(2026, 6, 10)
DURACAO_VIAGEM = 10 

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
    res = requests.post(url, headers=headers, data={"grant_type": "client_credentials"})
    return res.json()['access_token']

def buscar_passagens():
    token = obter_token()
    headers = {"Authorization": f"Bearer {token}"}
    pilha_de_resultados = [] # Aqui guardaremos ABSOLUTAMENTE TUDO o que encontrarmos

    data_atual = JANELA_INICIO
    while data_atual <= JANELA_FIM:
        d_ida = data_atual.strftime('%Y-%m-%d')
        d_volta = (data_atual + timedelta(days=DURACAO_VIAGEM)).strftime('%Y-%m-%d')
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        # Buscamos até 50 voos por dia para não perder nada
        params = {"originLocationCode": ORIGEM, "destinationLocationCode": DESTINO,
                  "departureDate": d_ida, "returnDate": d_volta,
                  "adults": 2, "nonStop": "true", "currencyCode": "BRL", "max": 50}
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            offers = res.json().get('data', [])
            for offer in offers:
                pilha_de_resultados.append(offer) # Adiciona cada voo na pilha única
        
        data_atual += timedelta(days=1)
    
    # AGORA SIM: Ordenamos a pilha inteira pelo preço e pegamos os 3 melhores do período
    pilha_de_resultados.sort(key=lambda x: float(x['price']['total']))
    return pilha_de_resultados[:3]

def formatar_voo(voo, rank):
    if not voo: return ""
    
    preco = voo['price']['total']
    cia = voo['validatingAirlineCodes'][0]
    it_ida = voo['itineraries'][0]['segments'][0]
    it_volta = voo['itineraries'][1]['segments'][0]
    
    num_ida, hora_ida = f"{it_ida['carrierCode']}{it_ida['number']}", it_ida['departure']['at'].replace('T', ' às ')
    num_volta, hora_volta = f"{it_volta['carrierCode']}{it_volta['number']}", it_volta['departure']['at'].replace('T', ' às ')
    
    d_ida, d_volta = it_ida['departure']['at'][:10], it_volta['departure']['at'][:10]
    
    link_latam = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={ORIGEM}&destination={DESTINO}&outbound={d_ida}&inbound={d_volta}&adults=2&trip=RT&cabin=economy"
    link_google = f"https://www.google.com/travel/flights?q=Flights%20from%20{ORIGEM}%20to%20{DESTINO}%20on%20{d_ida}%20through%20{d_volta}%20nonstop"

    return f"""
🏆 {rank}º MELHOR PREÇO DO PERÍODO: R$ {preco}
Companhia: {cia} {'(PREFERENCIAL)' if cia in ['LA', 'JJ'] else ''}
✈️ IDA: {num_ida} ({hora_ida})
✈️ VOLTA: {num_volta} ({hora_volta})
🔗 LINK LATAM: {link_latam}
🔗 GOOGLE FLIGHTS: {link_google}
--------------------------------------------
"""

def enviar_email(top_voos):
    corpo = "✈️ OS
