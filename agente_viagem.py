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
JANELA_FIM = datetime(2026, 6, 10)
DURACAO_VIAGEM = 10 # 10 dias de permanência

# --- CREDENCIAIS (Use os nomes dos segredos do GitHub) ---
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
    melhor_geral, melhor_latam = None, None

    data_atual = JANELA_INICIO
    while data_atual <= JANELA_FIM:
        data_ida = data_atual.strftime('%Y-%m-%d')
        data_volta = (data_atual + timedelta(days=DURACAO_VIAGEM)).strftime('%Y-%m-%d')
        
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": ORIGEM, "destinationLocationCode": DESTINO,
            "departureDate": data_ida, "returnDate": data_volta,
            "adults": 2, "nonStop": "true", # Somente voos diretos
            "currencyCode": "BRL", "max": 20
        }
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            offers = res.json().get('data', [])
            for offer in offers:
                preco = float(offer['price']['total'])
                cia = offer['validatingAirlineCodes'][0]
                
                if cia in ['LA', 'JJ']:
                    if not melhor_latam or preco < float(melhor_latam['price']['total']):
                        melhor_latam = offer
                if not melhor_geral or preco < float(melhor_geral['price']['total']):
                    melhor_geral = offer
        data_atual += timedelta(days=1)
    return melhor_geral, melhor_latam

def formatar_voo(voo, titulo):
    if not voo: return f"--- {titulo} ---\nNenhum voo direto encontrado nesta categoria.\n\n"
    
    preco = voo['price']['total']
    cia = voo['validatingAirlineCodes'][0]
    d_ida = voo['itineraries'][0]['segments'][0]['departure']['at'][:10]
    d_volta = voo['itineraries'][1]['segments'][0]['departure']['at'][:10]
    
    # Link LATAM Simplificado (sem T12:00:00 para evitar erro 404)
    link_latam = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={ORIGEM}&destination={DESTINO}&outbound={d_ida}&inbound={d_volta}&adults=2&trip=RT&cabin=economy"
    # Link Google Flights (Backup Seguro)
    link_google = f"https://www.google.com/travel/flights/search?tfs=CBwQAhoeagwIAhIIL20vMDR5cWxyB2p0cnVlQDA2MDFyBwgBEgNMSFQaHmoHCAESA0xIUnByB2p0cnVlQDA2MTFyDAgCEggvbS8wNHlx bHA&curr=BRL"
    
    return f"""
--- {titulo} ---
Companhia: {cia}
Preço Total (2 pessoas): R$ {preco}
Datas: {d_ida} até {d_volta}
Link Direto LATAM: {link_latam}
Link de Segurança (Google Flights): {link_google}
"""

def enviar_email(geral, latam):
    corpo = "✈️ RELATÓRIO DE PASSAGENS DIRETAS - LONDRES 2026\n\n"
    corpo += formatar_voo(latam, "OPÇÃO PREFERENCIAL LATAM")
    corpo += formatar_voo(geral, "OPÇÃO MAIS BARATA (GERAL)")
    
    msg = MIMEText(corpo)
    msg['Subject'] = f"✈️ Alerta: Londres Junho (10 dias)"
    msg['From'], msg['To'] = EMAIL_USER, EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())

if __name__ == "__main__":
    geral, latam = buscar_passagens()
    if geral or latam:
        enviar_email(geral, latam)
