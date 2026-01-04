import base64
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
DURACAO_VIAGEM = 15  # Dias de permanência para o roteiro Europa

# --- CREDENCIAIS (Puxando dos segredos do GitHub) ---
# Aqui usamos apenas os NOMES dos segredos que você criou nas configurações do GitHub
AMADEUS_KEY = os.getenv('AMADEUS_KEY')
AMADEUS_SECRET = os.getenv('AMADEUS_SECRET')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS') # Nome do segredo da senha de 16 dígitos

def obter_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    
    # Preparamos a sua chave e segredo no formato que o servidor exige
    auth_data = f"{AMADEUS_KEY}:{AMADEUS_SECRET}"
    encoded_auth_data = base64.b64encode(auth_data.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_auth_data}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"ERRO DA AMADEUS: {response.text}")
        exit(1)
        
    return response.json()['access_token']

def buscar_passagens():
    token = obter_token()
    headers = {"Authorization": f"Bearer {token}"}
    menor_preco = float('inf')
    melhor_voo = None

    # Pesquisa dia a dia na sua janela de 01 a 12 de junho de 2026
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
            "adults": 2, # Busca para você e sua esposa
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
    🤖 AGENTE DE IA: Passagem para Londres Encontrada!
    
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
