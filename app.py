import av
import cv2
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

st.title("Scanner Code-Barres Ultra-Fluide")


# Gestionnaire de traitement vidéo en arrière-plan
class BarcodeProcessor(VideoProcessorBase):

  def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
    # Convertit la frame WebRTC en image OpenCV (BGR)
    img = frame.to_ndarray(format="bgr24")

    # Détection du code-barres
    barcodes = decode(img)

    for barcode in barcodes:
      barcode_data = barcode.data.decode("utf-8")

      # Action : On dessine un rectangle vert autour du code détecté
      (x, y, w, h) = barcode.rect
      cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)

      # Optionnel : Écrit le texte du code sur la vidéo
      cv2.putText(
          img,
          barcode_data,
          (x, y - 10),
          cv2.FONT_HERSHEY_SIMPLEX,
          0.5,
          (0, 255, 0),
          2,
      )

      # Stocke le résultat dans la session Streamlit pour l'interface utilisateur
      if (
          "last_code" not in st.session_state
          or st.session_state.last_code != barcode_data
      ):
        st.session_state.last_code = barcode_data

    # Renvoie l'image (modifiée ou non) pour un affichage vidéo fluide à l'écran
    return av.VideoFrame.from_ndarray(img, format="bgr24")


# Lance le flux vidéo de manière optimisée pour les smartphones
ctx = webrtc_streamer(
    key="barcode-scanner-webrtc",
    video_processor_factory=BarcodeProcessor,
    # Utilisation du serveur STUN officiel de Google sans ambiguïté de port
    rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    },
    media_stream_constraints={"video": {"facingMode": "environment"}, "audio": False},
)

# Affiche le résultat dans l'interface Streamlit principale si un code est détecté
if "last_code" in st.session_state:
  st.success(f"Dernier code détecté : {st.session_state.last_code}")
