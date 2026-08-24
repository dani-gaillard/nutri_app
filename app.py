import av
import cv2
import queue
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer

st.title("Scanner Code-Barres")

# 1. Initialisation d'une file d'attente pour la communication entre les threads
if "barcode_queue" not in st.session_state:
    st.session_state.barcode_queue = queue.Queue()

# 2. Remplacement de la classe par un simple callback
def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)

    for barcode in barcodes:
        barcode_data = barcode.data.decode("utf-8")
        # Envoi du résultat au thread principal de Streamlit
        st.session_state.barcode_queue.put(barcode_data)

        # Dessine le rectangle vert de validation
        (x, y, w, h) = barcode.rect
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 4)

    return av.VideoFrame.from_ndarray(img, format="bgr24")

# 3. Configuration WebRTC mise à jour
ctx = webrtc_streamer(
    key="barcode-scanner-webrtc",
    video_frame_callback=video_frame_callback, # Utilisation du callback
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

# 4. Boucle d'écoute pour afficher le résultat en temps réel
if ctx.state.playing:
    result_placeholder = st.empty()
    result_placeholder.info("Conseil : Approchez ou éloignez doucement le code-barres du capteur pour aider la mise au point.")
    
    # Maintien du thread Streamlit actif tant que la vidéo tourne
    while True:
        try:
            # Attend un code-barres pendant 1 seconde, puis recommence
            detected_code = st.session_state.barcode_queue.get(timeout=1.0)
            result_placeholder.success(f"Code-barres détecté : **{detected_code}**")
        except queue.Empty:
            # Si le flux s'arrête, on sort de la boucle pour éviter de bloquer Streamlit
            if not ctx.state.playing:
                break