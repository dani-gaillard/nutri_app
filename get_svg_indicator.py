import re
import requests

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

    # --- 4. GÉOMÉTRIE DE LA JAUGE (320px de large) ---
    bar_w = 320
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
        <rect x="580" y="{by}" width="180" height="28" rx="6" fill="{bg}" stroke="{stroke}" stroke-width="1"/>
        <text x="670" y="{by + 19}" font-size="12" font-weight="bold" fill="{color}" text-anchor="middle">{text}</text>
        """
        by += 34

    if not badges:
        badges_svg = f'<text x="720" y="115" font-size="13" fill="#9e9e9e" font-style="italic" text-anchor="middle">Aucun badge</text>'

    product_name = str(prod.get('product_name', 'Produit inconnu'))[:45]

    # --- 6. COULEURS ---
    c_glu = "#0074f9"
    c_sug = "#004A9E"
    c_pro = "#00B209" # ou "#66bb6a"
    c_lip = "#ff5900"
    c_sat = "#9f3800"

    # --- 7. CONSTRUCTION DU SVG FINAL (3 Blocs) ---
    return f"""
    <svg width="790" height="260" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, sans-serif">
        <rect width="840" height="260" rx="14" fill="#ffffff" stroke="#e0e0e0" stroke-width="1.5"/>
        
        <!-- HEADER -->
        <rect x="0" y="0" width="840" height="42" rx="14" fill="#1565c0"/>
        <rect x="0" y="20" width="840" height="22" fill="#1565c0"/>
        <text x="20" y="26" fill="#ffffff" font-size="14" font-weight="bold">REPÈRE NUTRITIONNEL : {product_name.upper()}</text>
        
        <!-- SEPARATEURS VERTICAUX -->
        <line x1="200" y1="60" x2="200" y2="240" stroke="#eeeeee" stroke-width="2"/>
        <line x1="560" y1="60" x2="560" y2="240" stroke="#eeeeee" stroke-width="2"/>
        
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
                <rect x="0" y="0" width="{bar_w}" height="28" rx="6" ry="6"/>
            </clipPath>
        </defs>
        
        <g transform="translate(220, 127)" clip-path="url(#barClip)">
            <!-- Fond gris clair si 0 kcal -->
            <rect x="0" y="0" width="{bar_w}" height="28" fill="#f5f5f5"/>
            
            <!-- Glucides + Sucres -->
            <rect x="0" y="0" width="{w_glu:.1f}" height="28" fill="{c_glu}"/>
            <rect x="0" y="14" width="{w_sug:.1f}" height="14" fill="{c_sug}"/>
            
            <!-- Protéines -->
            <rect x="{w_glu:.1f}" y="0" width="{w_pro:.1f}" height="28" fill="{c_pro}"/>
            
            <!-- Lipides + Saturés (Hachure simulée par couleur sombre alignée à droite de sa section) -->
            <rect x="{w_glu + w_pro:.1f}" y="0" width="{w_lip:.1f}" height="28" fill="{c_lip}"/>
            <rect x="{w_glu + w_pro + w_lip - w_sat:.1f}" y="14" width="{w_sat:.1f}" height="14" fill="{c_sat}"/>

            <!-- Bordure optionnelle pour délimiter nettement l'extrémité droite -->
            <rect x="0" y="0" width="{bar_w}" height="28" rx="6" ry="6" fill="none" stroke="#ccc" stroke-width="1"/>
        </g>
        
        <!-- Textes sous jauge -->
        <text x="220" y="100" font-size="13" font-weight="bold" fill="{c_glu}">■ Glucides</text>
        <text x="220" y="117" font-size="13" fill="#333">{glu:.1f} g</text>
        <text x="220" y="170" font-size="11" font-weight="bold" fill="{c_sug}">dont sucres : {sug:.1f} g</text>
        
        <text x="330" y="100" font-size="13" font-weight="bold" fill="{c_pro}">■ Protéines</text>
        <text x="330" y="117" font-size="13" fill="#333">{pro:.1f} g</text>
        
        <text x="440" y="100" font-size="13" font-weight="bold" fill="{c_lip}">■ Lipides</text>
        <text x="440" y="117" font-size="13" fill="#333">{lip:.1f} g</text>
        <text x="440" y="170" font-size="11" font-weight="bold" fill="{c_sat}">dont saturés : {sat:.1f} g</text>

        <!-- BLOC 3 : Badges -->
        <text x="580" y="75" font-size="14" fill="#616161" font-weight="bold">Indicateurs</text>
        {badges_svg}
    </svg>"""










