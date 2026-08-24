import av
import cv2
import queue
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer

st.title("Scanner Code-Barres")

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
    
    # Espace vide réservé pour l'affichage du résultat
    result_placeholder = st.empty()
    
    # La boucle tourne UNIQUEMENT tant que la caméra est allumée
    while ctx.state.playing:
        try:
            # On écoute la file d'attente (timeout court pour ne pas bloquer l'interface)
            detected_code = barcode_queue.get(timeout=0.5)
            
            # Mise à jour de l'interface en temps réel
            result_placeholder.success(f"Code-barres détecté : **{detected_code}**")
            
            # Nettoyage de la file d'attente pour éviter que le même code 
            # ne s'affiche 50 fois si la caméra reste braquée dessus
            with barcode_queue.mutex:
                barcode_queue.queue.clear()
                
        except queue.Empty:
            # Si aucun code n'est détecté pendant ces 0.5 secondes, on recommence
            pass