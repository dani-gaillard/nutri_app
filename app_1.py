import av
import cv2
import queue
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer
import re
import requests
import numpy as np

def parse_portion(portion_str):
    """Extrait le poids en grammes depuis le champ serving_size."""
    if not portion_str:
        return 100.0
    match = re.search(r'([0-9]+(?:[.,][0-9]+)?)', str(portion_str))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 100.0

def fetch_and_build_indicator(barcode: str):
    """Récupère les données et retourne le code SVG sous forme de chaîne."""
    url = f'https://world.openfoodfacts.org/api/v2/product/{barcode}.json'
    headers = {'User-Agent': 'NutriCustomApp/1.0 (gaillard.dani.s3la@gmail.com)'}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error('Erreur réseau / API indisponible')
        return None

    data = response.json()
    if data.get('status') != 1:
        st.warning('Produit non trouvé dans Open Food Facts')
        return None

    prod = data['product']
    nutri = prod.get('nutriments', {})

    portion_g = parse_portion(prod.get('serving_size', '100g'))
    ratio = portion_g / 100.0

    kcal = round(nutri.get('energy-kcal_100g', 0) * ratio)
    glu = round(nutri.get('carbohydrates_100g', 0) * ratio, 1)
    sug = round(nutri.get('sugars_100g', 0) * ratio, 1)
    lip = round(nutri.get('fat_100g', 0) * ratio, 1)
    sat = round(nutri.get('saturated-fat_100g', 0) * ratio, 1)
    pro = round(nutri.get('proteins_100g', 0) * ratio, 1)
    fib = round(nutri.get('fiber_100g', 0) * ratio, 1)
    salt = round(nutri.get('salt_100g', 0) * ratio, 2)
    nova = prod.get('nova_group', None)

    cal_glu = glu * 4
    cal_pro = pro * 4
    cal_lip = lip * 9
    total_cal = max(cal_glu + cal_pro + cal_lip, 1)

    pct_glu = (cal_glu / total_cal) * 100
    pct_pro = (cal_pro / total_cal) * 100
    pct_lip = (cal_lip / total_cal) * 100

    bar_width = 380
    w_glu = (pct_glu / 100) * bar_width
    w_pro = (pct_pro / 100) * bar_width
    w_lip = (pct_lip / 100) * bar_width

    badges = []
    if fib >= 2.5:
        badges.append(('🌿 Riche en fibres', '#2e7d32'))
    if salt >= 0.5:
        badges.append(('⚠️ Fort en sel', '#d32f2f'))
    if nova == 4:
        badges.append(('🏭 Ultra-transformé', '#c2185b'))

    product_name = prod.get('product_name', 'Produit')[:35]
    badges_svg = ''
    bx = 20
    for b_text, b_color in badges:
        badges_svg += f"""
          <rect x="{bx}" y="205" width="130" height="26" rx="6" fill="{b_color}" opacity="0.15"/>
          <text x="{bx+65}" y="222" font-size="11" font-weight="bold" fill="{b_color}" text-anchor="middle">{b_text}</text>
        """
        bx += 140

    # Retourne directement le SVG (sans l'écrire dans un fichier)
    return f"""<svg width="440" height="255" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, sans-serif">
        <rect width="440" height="255" rx="14" fill="#ffffff" stroke="#e0e0e0" stroke-width="1.5"/>
        <rect x="0" y="0" width="440" height="42" rx="14" fill="#1565c0"/>
        <text x="20" y="26" fill="#ffffff" font-size="14" font-weight="bold">{product_name}</text>
        <text x="420" y="26" fill="#bbdefb" font-size="12" text-anchor="end">Portion : {portion_g:g}g</text>
        <text x="20" y="72" font-size="13" fill="#616161">Énergie apportée</text>
        <text x="20" y="98" font-size="24" font-weight="800" fill="#2e7d32">{kcal} <tspan font-size="14" font-weight="normal">kcal</tspan></text>
        <g transform="translate(20, 115)">
            <rect x="0" y="0" width="{w_glu:.1f}" height="22" fill="#0288d1" rx="3"/>
            <rect x="{w_glu:.1f}" y="0" width="{w_pro:.1f}" height="22" fill="#43a047" rx="3"/>
            <rect x="{w_glu + w_pro:.1f}" y="0" width="{w_lip:.1f}" height="22" fill="#fbc02d" rx="3"/>
        </g>
        <text x="20" y="155" font-size="11" fill="#333">
            <tspan fill="#0288d1" font-weight="bold">■ Glucides {pct_glu:.0f}%</tspan> ({glu}g, dont {sug}g sucres)  
            <tspan fill="#43a047" font-weight="bold">■ Prot. {pct_pro:.0f}%</tspan> ({pro}g)  
            <tspan fill="#f57f17" font-weight="bold">■ Lipides {pct_lip:.0f}%</tspan> ({lip}g, dont {sat}g sat.)
        </text>
        <line x1="20" y1="185" x2="420" y2="185" stroke="#eeeeee" stroke-width="1"/>
        {badges_svg}
    </svg>"""

# --- Interface Streamlit ---
st.title("Scanner Nutritionnel")

# 1. Création de la file d'attente dans la session
if "barcode_queue" not in st.session_state:
    st.session_state.barcode_queue = queue.Queue()

# 2. L'ASTUCE EST ICI : On stocke la référence dans une variable locale.
# Le thread WebRTC utilisera cette variable locale et ne fera pas appel 
# à st.session_state, évitant ainsi l'erreur de contexte.
barcode_queue = st.session_state.barcode_queue

def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)

    for barcode in barcodes:
        barcode_data = barcode.data.decode("utf-8")
        
        # On utilise la variable locale ici !
        barcode_queue.put(barcode_data)

        # Dessin du rectangle de validation
        (x, y, w, h) = barcode.rect
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 4)

    return av.VideoFrame.from_ndarray(img, format="bgr24")

# 3. Configuration WebRTC
ctx = webrtc_streamer(
    key="barcode-scanner",
    video_frame_callback=video_frame_callback,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={
        "video": {
            "facingMode": "environment",
            "width": {"ideal": 1280, "min": 640},
            "height": {"ideal": 720, "min": 480},
            "frameRate": {"ideal": 20},
        },
        "audio": False,
    },
)

# 4. Affichage des résultats
if ctx.state.playing:
    st.info("Scanner actif. Placez un code-barres devant la caméra.")
    
    # Création d'un espace dynamique. 
    # Tout ce qui sera mis dedans écrasera le contenu précédent.
    display_placeholder = st.empty()
    
    # On garde en mémoire le dernier code pour éviter de recalculer le même produit en boucle
    last_scanned_code = None
    
    # La boucle tourne UNIQUEMENT tant que la caméra est allumée
    while ctx.state.playing:
        try:
            # On écoute la file d'attente (timeout court pour ne pas bloquer l'interface)
            detected_code = barcode_queue.get(timeout=0.5)
            
            # On met à jour l'affichage SEULEMENT si c'est un nouveau produit
            if detected_code != last_scanned_code:
                last_scanned_code = detected_code
                
                # On utilise "with" pour injecter le contenu dans le placeholder
                with display_placeholder.container():
                    st.success(f"Code-barres détecté : **{detected_code}**")

                    # Génération du SVG
                    svg = fetch_and_build_indicator(detected_code)
                    
                    if svg:
                        # Affiche le code SVG directement dans l'interface web
                        st.markdown(f"<div>{svg}</div>", unsafe_allow_html=True)
            
            # Nettoyage de la file d'attente pour éviter l'accumulation
            with barcode_queue.mutex:
                barcode_queue.queue.clear()
                
        except queue.Empty:
            # Si aucun code n'est détecté pendant ces 0.5 secondes, on recommence
            pass