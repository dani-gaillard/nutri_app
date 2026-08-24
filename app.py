import re
import requests
import cv2
import numpy as np
import streamlit as st
from pyzbar.pyzbar import decode
from camera_input_live import camera_input_live



def parse_portion(portion_str):
  """Extrait le poids en grammes depuis le champ serving_size."""
  if not portion_str:
    return 100.0
  match = re.search(r'([0-9]+(?:[.,][0-9]+)?)', str(portion_str))
  if match:
    return float(match.group(1).replace(',', '.'))
  return 100.0


def fetch_and_build_indicator(barcode: str, output_file='indicateur.svg'):
  # 1. Appel API Open Food Facts v2
  url = f'https://world.openfoodfacts.org/api/v2/product/{barcode}.json'
  headers = {'User-Agent': 'NutriCustomApp/1.0 (gaillard.dani.s3la@gmail.com)'}

  response = requests.get(url, headers=headers)
  if response.status_code != 200:
    print('Erreur réseau / API indisponible')
    return False

  data = response.json()
  if data.get('status') != 1:
    print('Produit non trouvé dans Open Food Facts')
    return False

  prod = data['product']
  nutri = prod.get('nutriments', {})

  # 2. Calcul des valeurs par portion
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

  # 3. Répartition énergétique (% kcal)
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

  # 4. Badges et alertes
  badges = []
  if fib >= 2.5:  # ~10-15% des VNR
    badges.append(('🌿 Riche en fibres', '#2e7d32'))
  if salt >= 0.5:  # alerte sel
    badges.append(('⚠️ Fort en sel', '#d32f2f'))
  if nova == 4:
    badges.append(('🏭 Ultra-transformé', '#c2185b'))

  # Construction SVG
  product_name = prod.get('product_name', 'Produit')[:35]
  badges_svg = ''
  bx = 20
  for b_text, b_color in badges:
    badges_svg += f"""
      <rect x="{bx}" y="205" width="130" height="26" rx="6" fill="{b_color}" opacity="0.15"/>
      <text x="{bx+65}" y="222" font-size="11" font-weight="bold" fill="{b_color}" text-anchor="middle">{b_text}</text>
    """
    bx += 140

  svg = f"""<svg width="440" height="255" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, sans-serif">
    <rect width="440" height="255" rx="14" fill="#ffffff" stroke="#e0e0e0" stroke-width="1.5"/>
    
    <!-- En-tête -->
    <rect x="0" y="0" width="440" height="42" rx="14" fill="#1565c0"/>
    <text x="20" y="26" fill="#ffffff" font-size="14" font-weight="bold">{product_name}</text>
    <text x="420" y="26" fill="#bbdefb" font-size="12" text-anchor="end">Portion : {portion_g:g}g</text>

    <!-- Calories -->
    <text x="20" y="72" font-size="13" fill="#616161">Énergie apportée</text>
    <text x="20" y="98" font-size="24" font-weight="800" fill="#2e7d32">{kcal} <tspan font-size="14" font-weight="normal">kcal</tspan></text>

    <!-- Jauge tripartite -->
    <g transform="translate(20, 115)">
      <rect x="0" y="0" width="{w_glu:.1f}" height="22" fill="#0288d1" rx="3"/>
      <rect x="{w_glu:.1f}" y="0" width="{w_pro:.1f}" height="22" fill="#43a047" rx="3"/>
      <rect x="{w_glu + w_pro:.1f}" y="0" width="{w_lip:.1f}" height="22" fill="#fbc02d" rx="3"/>
    </g>

    <!-- Détail Macros -->
    <text x="20" y="155" font-size="11" fill="#333">
      <tspan fill="#0288d1" font-weight="bold">■ Glucides {pct_glu:.0f}%</tspan> ({glu}g, dont {sug}g sucres)  
      <tspan fill="#43a047" font-weight="bold">■ Prot. {pct_pro:.0f}%</tspan> ({pro}g)  
      <tspan fill="#f57f17" font-weight="bold">■ Lipides {pct_lip:.0f}%</tspan> ({lip}g, dont {sat}g sat.)
    </text>

    <!-- Badges -->
    <line x1="20" y1="185" x2="420" y2="185" stroke="#eeeeee" stroke-width="1"/>
    {badges_svg}
  </svg>"""

  with open(output_file, 'w', encoding='utf-8') as f:
    f.write(svg)
  print(f'Indicateur généré avec succès : {output_file}')
  return True





st.title("Scanner de code-barres en direct")

# Capture le flux de la caméra du téléphone
image_data = camera_input_live(key="barcode_scanner")

if image_data is not None:
  # Convertit l'image reçue en tableau numpy
  bytes_data = image_data.getvalue()
  cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

  # Décode les codes-barres présents dans l'image
  barcodes = decode(cv2_img)

  for barcode in barcodes:
    barcode_data = barcode.data.decode("utf-8")
    barcode_type = barcode.type

    # Affiche le résultat immédiatement
    st.success(
        f"Code détecté : {barcode_data} (Type : {barcode_type})"
    )

    # Ajoutez ici votre fonction personnalisée à déclencher
    # ma_fonction_declenchee(barcode_data)
    fetch_and_build_indicator(barcode_data, 'test.svg')

