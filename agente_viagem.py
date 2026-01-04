import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE PESQUISA ---
ORIGEM = "GRU"
DESTINO = "LHR"
JANELA_INICIO = datetime(2026, 6, 1)
JANELA_FIM = datetime(2026, 6, 12)
DURACAO_VIAGEM = 15  # Dias de permanência (ajuste se preferir)

# --- CREDENCIAIS (Serão puxadas do GitHub por segurança) ---
AMADEUS_KEY = os.getenv('9y1tWaZ5kKTx1QggHuNoe5lhMygAqodx')
AMADEUS_SECRET = os.getenv('RE4s6HOQxz4oX4NH')
EMAIL_USER = os.getenv('arq.raphaelmartin@gmail.com')
EMAIL_PASS = os.getenv('rdad vkbo pkhi qjhi') # Aquela senha de 16 dígitos

def obter_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_KEY,
        "client_secret": AMADEUS_SECRET
    }
    response = requests.post(url, data=data)
    return response.json()['access_token']

def buscar_passagens():
    token = obter_token()
    headers = {"Authorization": f"Bearer {token}"}
    menor_preco = float('inf')
    melhor_voo = None

    # Pesquisa dia a dia na sua janela de 01 a 12 de junho
    data_atual = JANELA_INICIO
    while data_atual <= JANELA_FIM:
        data_ida = data_atual.strftime('%Y-%m-%d')
        data_volta = (data_atual + timedelta(days=DURACAO_VIAGEM)).strftime('%Y-%m-%d')
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": ORIGEM,
            "destinationLocationCode": DESTINO,
            "departureDate": data_ida,
            "returnDate": data_volta,
            "adults": 2, # Pesquisa para o casal
            "currencyCode": "BRL",
            "max": 5
        }
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            offers = res.json().get('data', [])
            for offer in offers:
                preco = float(offer['price']['total'])
                if preco < menor_preco:
                    menor_preco = preco
                    melhor_voo = offer
        
        data_atual += timedelta(days=1)
    
    return melhor_voo

def enviar_email(voo):
    if not voo:
        return

    preco = voo['price']['total']
    ida = voo['itineraries'][0]['segments'][0]['departure']['at']
    cia = voo['validatingAirlineCodes'][0]
    
    msg_corpo = f"""
    🤖 AGENTE DE IA: Passagem Encontrada!
    
    Menor valor (Total para 2 pessoas): R$ {preco}
    Companhia: {cia}
    Data de Ida: {ida}
    
    Confira direto no site da {cia} ou Google Flights.
    """
    
    msg = MIMEText(msg_corpo)
    msg['Subject'] = f"✈️ Alerta de Preço: Londres R$ {preco}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())

if __name__ == "__main__":
    resultado = buscar_passagens()
    if resultado:
        enviar_email(resultado)