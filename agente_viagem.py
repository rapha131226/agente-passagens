import base64
import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE PESQUISA ---
ORIGEM, DESTINO = "GRU", "LHR"
JANELA_INICIO = datetime(2026, 6, 1)
JANELA_FIM = datetime(2026, 6, 10)
DURACAO_VIAGEM = 10 

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
    melhor_geral, melhor_latam = None, None

    data_atual = JANELA_INICIO
    while data_atual <= JANELA_FIM:
        d_ida = data_atual.strftime('%Y-%m-%d')
        d_volta = (data_atual + timedelta(days=DURACAO_VIAGEM)).strftime('%Y-%m-%d')
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {"originLocationCode": ORIGEM, "destinationLocationCode": DESTINO,
                  "departureDate": d_ida, "returnDate": d_volta,
                  "adults": 2, "nonStop": "true", "currencyCode": "BRL", "max": 10}
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            offers = res.json().get('data', [])
            for offer in offers:
                preco = float(offer['price']['total'])
                cia = offer['validatingAirlineCodes'][0]
                if cia in ['LA', 'JJ']:
                    if not melhor_latam or preco < float(melhor_latam['price']['total']): melhor_latam = offer
                if not melhor_geral or preco < float(melhor_geral['price']['total']): melhor_geral = offer
        data_atual += timedelta(days=1)
    return melhor_geral, melhor_latam

def formatar_voo(voo, titulo):
    if not voo: return f"--- {titulo} ---\nNenhum voo direto encontrado.\n\n"
    
    preco = voo['price']['total']
    # Extração de detalhes técnicos para busca manual segura
    itinerario_ida = voo['itineraries'][0]['segments'][0]
    itinerario_volta = voo['itineraries'][1]['segments'][0]
    
    num_voo_ida = f"{itinerario_ida['carrierCode']}{itinerario_ida['number']}"
    hora_ida = itinerario_ida['departure']['at'].replace('T', ' às ')
    
    num_voo_volta = f"{itinerario_volta['carrierCode']}{itinerario_volta['number']}"
    hora_volta = itinerario_volta['departure']['at'].replace('T', ' às ')

    d_ida = itinerario_ida['departure']['at'][:10]
    d_volta = itinerario_volta['departure']['at'][:10]
    
    # Links robustos
    link_latam = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={ORIGEM}&destination={DESTINO}&outbound={d_ida}&inbound={d_volta}&adults=2&trip=RT&cabin=economy"
    link_google = f"https://www.google.com/travel/flights?q=Flights%20from%20{ORIGEM}%20to%20{DESTINO}%20on%20{d_ida}%20through%20{d_volta}%20nonstop"

    return f"""
--- {titulo} ---
💰 PREÇO TOTAL (2 pessoas): R$ {preco}
✈️ IDA: Voo {num_voo_ida} | Partida: {hora_ida}
✈️ VOLTA: Voo {num_voo_volta} | Partida: {hora_volta}

🔗 LINK LATAM: {link_latam}
🔗 BUSCA GOOGLE: {link_google}
"""

def enviar_email(geral, latam):
    corpo = "✈️ RELATÓRIO DE VOOS DIRETOS - LONDRES JUNHO 2026\n\n"
    corpo += formatar_voo(latam, "OPÇÃO PRIORITÁRIA LATAM")
    corpo += formatar_voo(geral, "OPÇÃO MAIS BARATA (GERAL)")
    
    msg = MIMEText(corpo)
    msg['Subject'] = f"✈️ Alerta: Londres Junho (10 dias)"
    msg['From'], msg['To'] = EMAIL_USER, EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())

if __name__ == "__main__":
    geral, latam = buscar_passagens()
    if geral or latam: enviar_email(geral, latam)
