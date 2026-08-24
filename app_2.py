import av
import cv2
import queue
import re
import requests
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer

def parse_portion(portion_str):
    """Extrait le poids en grammes depuis le champ serving_size."""
    if not portion_str:
        return 100.0
    match = re.search(r'([0-9]+(?:[.,][0-9]+)?)', str(portion_str))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 100.0

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except ValueError:
        return default

def fetch_and_build_indicator(barcode: str):
    """Récupère les données OFF et retourne le SVG du repère nutritionnel (Spec V2)."""
    url = f'https://world.openfoodfacts.org/api/v2/product/{barcode}.json'
    headers = {'User-Agent': 'NutriCustomApp/2.0 (gaillard.dani.s3la@gmail.com)'}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return "<div style='color:red;'>Erreur réseau / API indisponible</div>"

    data = response.json()
    if data.get('status') != 1:
        return "<div style='color:orange;'>Produit non trouvé dans Open Food Facts</div>"

    prod = data['product']
    nutri = prod.get('nutriments', {})

    # --- 1. PORTION ---
    portion_g = safe_float(prod.get('serving_quantity'))
    if portion_g <= 0:
        portion_g = parse_portion(prod.get('serving_size', '100g'))
    ratio = portion_g / 100.0

    # --- 2. EXTRACTION DES MACROS (Priorité au _serving, sinon calcul via _100g) ---
    def get_nut(key):
        val_serving = nutri.get(f"{key}_serving")
        if val_serving is not None and val_serving != "":
            return safe_float(val_serving)
        return safe_float(nutri.get(f"{key}_100g")) * ratio

    glu = get_nut('carbohydrates')
    sug = get_nut('sugars')
    pro = get_nut('proteins')
    lip = get_nut('fat')
    sat = get_nut('saturated-fat')

    # --- 3. CALCUL KILOCALORIES (Atwater 4-4-9) ---
    cal_glu = glu * 4.0
    cal_pro = pro * 4.0
    cal_lip = lip * 9.0
    kcal_total = cal_glu + cal_pro + cal_lip
    kcal_display = round(kcal_total)
    
    # Sécurité pour éviter division par zéro sur des produits type "Eau"
    kcal_math = max(kcal_total, 1.0) 

    # --- 4. GÉOMÉTRIE DE LA JAUGE (380px de large) ---
    bar_w = 380
    w_glu = (cal_glu / kcal_math) * bar_w
    w_pro = (cal_pro / kcal_math) * bar_w
    w_lip = (cal_lip / kcal_math) * bar_w
    
    # Sous-niveaux (capés pour ne pas déborder visuellement de leur parent)
    w_sug = min((sug * 4.0 / kcal_math) * bar_w, w_glu)
    w_sat = min((sat * 9.0 / kcal_math) * bar_w, w_lip)

    # --- 5. LOGIQUE DES BADGES ---
    badges = []
    
    # Fibres
    fib_100g = safe_float(nutri.get('fiber_100g'))
    if fib_100g >= 6.0:
        badges.append(('🌿 Riche en fibres', '#2e7d32', '#e8f5e9')) # Texte, Bordure/Texte, Fond
    elif fib_100g >= 3.0:
        badges.append(('🌿 Source de fibres', '#2e7d32', '#e8f5e9'))

    # Micronutriments (Les VNR sont converties en grammes. Ex: Fer = 14mg -> 0.014g -> 15% = 0.0021g)
    if get_nut('iron') >= 0.0021:
        badges.append(('🛡️ Source de Fer', '#1565c0', '#e3f2fd'))
    if get_nut('calcium') >= 0.120:
        badges.append(('🦴 Source de Calcium', '#1565c0', '#e3f2fd'))
    if get_nut('vitamin-c') >= 0.012:
        badges.append(('🍊 Source de Vit. C', '#1565c0', '#e3f2fd'))

    # Sel (Alerte si > 1.5g/100g ou > 0.75g/portion)
    salt_100g = safe_float(nutri.get('salt_100g'))
    salt_serving = get_nut('salt')
    if salt_100g >= 1.5 or salt_serving >= 0.75:
        badges.append(('⚠️ Fort en sel', '#c62828', '#ffebee'))

    # NOVA
    nova = prod.get('nova_group')
    if nova == 4:
        badges.append(('🏭 ULTRA-TRANSFORMÉ', '#ffffff', '#c62828'))

    # Génération du code SVG des badges
    badges_svg = ""
    by = 95
    for text, color, bg in badges:
        # Style spécifique si le badge est Nova 4 (Fond plein)
        stroke = "none" if bg == '#c62828' else color
        badges_svg += f"""
        <rect x="630" y="{by}" width="180" height="28" rx="6" fill="{bg}" stroke="{stroke}" stroke-width="1"/>
        <text x="720" y="{by + 19}" font-size="12" font-weight="bold" fill="{color}" text-anchor="middle">{text}</text>
        """
        by += 34

    if not badges:
        badges_svg = f'<text x="720" y="115" font-size="13" fill="#9e9e9e" font-style="italic" text-anchor="middle">Aucun badge</text>'

    product_name = str(prod.get('product_name', 'Produit inconnu'))[:45]

    # --- 6. CONSTRUCTION DU SVG FINAL (3 Blocs) ---
    return f"""
    <svg width="840" height="260" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, sans-serif">
        <rect width="840" height="260" rx="14" fill="#ffffff" stroke="#e0e0e0" stroke-width="1.5"/>
        
        <!-- HEADER -->
        <rect x="0" y="0" width="840" height="42" rx="14" fill="#1565c0"/>
        <rect x="0" y="20" width="840" height="22" fill="#1565c0"/>
        <text x="20" y="26" fill="#ffffff" font-size="14" font-weight="bold">VOTRE REPÈRE NUTRITIONNEL : {product_name.upper()}</text>
        
        <!-- SEPARATEURS VERTICAUX -->
        <line x1="200" y1="60" x2="200" y2="240" stroke="#eeeeee" stroke-width="2"/>
        <line x1="610" y1="60" x2="610" y2="240" stroke="#eeeeee" stroke-width="2"/>
        
        <!-- BLOC 1 : Portion & Kcal -->
        <text x="100" y="75" font-size="14" fill="#616161" font-weight="bold" text-anchor="middle">Portion</text>
        <text x="100" y="95" font-size="16" fill="#333" text-anchor="middle">{portion_g:g} g</text>
        
        <circle cx="100" cy="160" r="46" fill="#e8f5e9" stroke="#43A047" stroke-width="3"/>
        <text x="100" y="160" font-size="26" font-weight="800" fill="#2e7d32" text-anchor="middle">{kcal_display}</text>
        <text x="100" y="182" font-size="14" font-weight="bold" fill="#2e7d32" text-anchor="middle">kcal</text>

        <!-- BLOC 2 : Jauge Macros -->
        <text x="220" y="75" font-size="14" fill="#616161" font-weight="bold">Répartition énergétique</text>
        
        <!-- ClipPath pour arrondir toute la jauge -->
        <defs>
            <clipPath id="barClip">
                <rect x="0" y="0" width="{bar_w}" height="28" rx="6"/>
            </clipPath>
        </defs>
        
        <g transform="translate(220, 100)" clip-path="url(#barClip)">
            <!-- Fond gris clair si 0 kcal -->
            <rect x="0" y="0" width="{bar_w}" height="28" fill="#f5f5f5"/>
            
            <!-- Glucides + Sucres -->
            <rect x="0" y="0" width="{w_glu:.1f}" height="28" fill="#42a5f5"/>
            <rect x="{w_glu - w_sug:.1f}" y="0" width="{w_sug:.1f}" height="28" fill="#1565c0"/>
            
            <!-- Protéines -->
            <rect x="{w_glu:.1f}" y="0" width="{w_pro:.1f}" height="28" fill="#66bb6a"/>
            
            <!-- Lipides + Saturés (Hachure simulée par couleur sombre alignée à droite de sa section) -->
            <rect x="{w_glu + w_pro:.1f}" y="0" width="{w_lip:.1f}" height="28" fill="#ffa726"/>
            <rect x="{w_glu + w_pro + w_lip - w_sat:.1f}" y="0" width="{w_sat:.1f}" height="28" fill="#e65100"/>
        </g>
        
        <!-- Textes sous jauge -->
        <text x="220" y="155" font-size="13" font-weight="bold" fill="#1565c0">■ Glucides</text>
        <text x="220" y="172" font-size="13" fill="#333">{glu:.1f} g</text>
        <text x="220" y="190" font-size="11" fill="#757575">dont sucres : {sug:.1f} g</text>
        
        <text x="330" y="155" font-size="13" font-weight="bold" fill="#2e7d32">■ Protéines</text>
        <text x="330" y="172" font-size="13" fill="#333">{pro:.1f} g</text>
        
        <text x="440" y="155" font-size="13" font-weight="bold" fill="#e65100">■ Lipides</text>
        <text x="440" y="172" font-size="13" fill="#333">{lip:.1f} g</text>
        <text x="440" y="190" font-size="11" fill="#757575">dont saturés : {sat:.1f} g</text>

        <!-- BLOC 3 : Badges -->
        <text x="630" y="75" font-size="14" fill="#616161" font-weight="bold">Indicateurs</text>
        {badges_svg}
    </svg>"""

# --- Interface Streamlit (Identique à ta version corrigée) ---
st.set_page_config(layout="wide") # Conseillé pour afficher la carte SVG de 840px
st.title("Scanner Nutritionnel")

if "barcode_queue" not in st.session_state:
    st.session_state.barcode_queue = queue.Queue()
barcode_queue = st.session_state.barcode_queue

def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)
    for barcode in barcodes:
        barcode_queue.put(barcode.data.decode("utf-8"))
        (x, y, w, h) = barcode.rect
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 4)
    return av.VideoFrame.from_ndarray(img, format="bgr24")

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

if ctx.state.playing:
    st.info("Scanner actif. Placez un code-barres devant la caméra.")
    display_placeholder = st.empty()
    last_scanned_code = None
    
    while ctx.state.playing:
        try:
            detected_code = barcode_queue.get(timeout=0.5)
            if detected_code != last_scanned_code:
                last_scanned_code = detected_code
                with display_placeholder.container():
                    st.success(f"Code-barres détecté : **{detected_code}**")
                    svg = fetch_and_build_indicator(detected_code)
                    if svg:
                        #st.markdown(f"<div style='display:flex; justify-content:center;'>{svg}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div>{svg}</div>", unsafe_allow_html=True)
            with barcode_queue.mutex:
                barcode_queue.queue.clear()
        except queue.Empty:
            pass