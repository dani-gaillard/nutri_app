from get_svg_indicator import fetch_and_build_indicator

import av
import cv2
import queue
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer
import base64

# --- Interface Streamlit ---
st.set_page_config(layout="wide")
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

# ASTUCE CAMÉRA : On crée 3 colonnes et on met la caméra dans celle du milieu (la 2ème)
# Les ratios [1, 2, 1] signifient que la colonne centrale est 2x plus grande que les côtés.
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    ctx = webrtc_streamer(
        key="barcode-scanner",
        video_frame_callback=video_frame_callback,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={
            "video": {
                "facingMode": "environment",
                "width": {"ideal": 1280, "min": 640},
                "height": {"ideal": 720, "min": 480}
            }, 
            "audio": False
        },
        # Cela réduit la taille VISUELLE de la vidéo sans baisser la qualité de la capture
        video_html_attrs={
            "style": {
                "width": "100%", 
                "maxWidth": "500px", 
                "margin": "0 auto", 
                "borderRadius": "10px"
            },
            "autoPlay": True,
            "playsInline": True
        }
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
                    svg_content = fetch_and_build_indicator(detected_code)
                    
                    if svg_content:
                        # Si c'est bien un SVG (et pas un message d'erreur de l'API)
                        if svg_content.strip().startswith("<svg"):
                            # On convertit le SVG en image Base64 pour empêcher 
                            # Streamlit de l'interpréter comme du texte Markdown
                            b64_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
                            img_html = f'<img src="data:image/svg+xml;base64,{b64_svg}" style="max-width: 100%; height: auto; border-radius: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">'
                            st.markdown(f"<div style='display:flex; justify-content:center; margin-top: 20px;'>{img_html}</div>", unsafe_allow_html=True)
                        else:
                            # C'est un message d'erreur <div> (ex: "Produit non trouvé")
                            st.markdown(svg_content, unsafe_allow_html=True)
                            
            with barcode_queue.mutex:
                barcode_queue.queue.clear()
        except queue.Empty:
            pass