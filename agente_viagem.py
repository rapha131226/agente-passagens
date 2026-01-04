import base64
import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE PESQUISA (Junho/2026) ---
ORIGEM = "GRU"
DESTINO = "LON" # Busca em TODOS os aeroportos de Londres (Heathrow, Gatwick, etc.)
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
    pilha_de_resultados = []

    data_atual = JANELA_INICIO
    while data_atual <= JANELA_FIM:
        d_ida = data_atual.strftime('%Y-%m-%d')
        d_volta = (data_atual + timedelta(days=DURACAO_VIAGEM)).strftime('%Y-%m-%d')
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {"originLocationCode": ORIGEM, "destinationLocationCode": DESTINO,
                  "departureDate": d_ida, "returnDate": d_volta,
                  "adults": 2, "nonStop": "true", "currencyCode": "BRL", "max": 50}
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            offers = res.json().get('data', [])
            for offer in offers:
                pilha_de_resultados.append(offer)
        
        data_atual += timedelta(days=1)
    
    # Ordena a pilha inteira pelo preço e pega os 3 melhores do período
    pilha_de_resultados.sort(key=lambda x: float(x['price']['total']))
    return pilha_de_resultados[:3]

def formatar_voo(voo, rank):
    if not voo: return ""
    
    preco = voo['price']['total']
    cia = voo['validatingAirlineCodes'][0]
    it_ida = voo['itineraries'][0]['segments'][0]
    it_volta = voo['itineraries'][1]['segments'][0]
    
    # Identifica o aeroporto específico (ex: LHR ou LGW)
    aero_ida = it_ida['arrival']['iataCode']
    aero_volta = it_volta['departure']['iataCode']
    
    num_ida, hora_ida = f"{it_ida['carrierCode']}{it_ida['number']}", it_ida['departure']['at'].replace('T', ' às ')
    num_volta, hora_volta = f"{it_volta['carrierCode']}{it_volta['number']}", it_volta['departure']['at'].replace('T', ' às ')
    
    d_ida, d_volta = it_ida['departure']['at'][:10], it_volta['departure']['at'][:10]
    
    link_latam = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={ORIGEM}&destination={aero_ida}&outbound={d_ida}&inbound={d_volta}&adults=2&trip=RT&cabin=economy"
    link_google = f"https://www.google.com/travel/flights?q=Flights%20from%20{ORIGEM}%20to%20{aero_ida}%20on%20{d_ida}%20through%20{d_volta}%20nonstop"

    return f"""
🏆 {rank}º MENOR PREÇO DO PERÍODO: R$ {preco}
Companhia: {cia} | Aeroporto: {aero_ida}
✈️ IDA: {num_ida} ({hora_ida})
✈️ VOLTA: {num_volta} ({hora_volta})
🔗 LINK LATAM: {link_latam}
🔗 GOOGLE FLIGHTS: {link_google}
--------------------------------------------
"""

def enviar_email(top_voos):
    corpo = "✈️ OS 3 MELHORES PREÇOS ENCONTRADOS EM LONDRES (JANELA: 01 A 10/JUN)\n"
    corpo += "Pesquisa abrangendo todos os aeroportos da cidade para máxima economia.\n\n"
    
    for i, voo in enumerate(top_voos):
        corpo += formatar_voo(voo, i+1)
    
    msg = MIMEText(corpo)
    msg['Subject'] = f"✈️ TOP 3 GERAL LON: Junho desde R$ {top_voos[0]['price']['total'] if top_voos else 'N/A'}"
    msg['From'], msg['To'] = EMAIL_USER, EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())

if __name__ == "__main__":
    melhores = buscar_passagens()
    if melhores:
        enviar_email(melhores)
