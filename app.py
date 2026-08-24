import av
import cv2
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

st.title("Scanner Code-Barres")


class BarcodeProcessor(VideoProcessorBase):

  def __init__(self) -> None:
    self.found_code = None

  def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")

    # Étape 1 : Amélioration de l'image (Nuances de gris + Contraste)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Étape 2 : Détection pyzbar
    barcodes = decode(gray)

    for barcode in barcodes:
      self.found_code = barcode.data.decode("utf-8")

      # Dessine le rectangle vert de validation si détecté
      (x, y, w, h) = barcode.rect
      cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 4)

    return av.VideoFrame.from_ndarray(img, format="bgr24")


# Configuration WebRTC avancée pour mobiles
ctx = webrtc_streamer(
    key="barcode-scanner-webrtc",
    video_processor_factory=BarcodeProcessor,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    # FORÇAGE DE LA RÉSOLUTION & PARAMÈTRES MOBILES
    media_stream_constraints={
        "video": {
            "facingMode": "environment",  # Caméra arrière
            "width": {"ideal": 1280, "min": 640},  # Force une bonne résolution
            "height": {"ideal": 720, "min": 480},
            "frameRate": {"ideal": 20},
        },
        "audio": False,
    },
)

# Zone d'affichage du résultat
if ctx.video_processor:
  detected_code = getattr(ctx.video_processor, "found_code", None)

  if detected_code:
    st.success(f"Code-barres détecté : {detected_code}")
    # Optionnel : bouton pour réinitialiser la recherche
    if st.button("Scanner un autre produit"):
      ctx.video_processor.found_code = None
      st.rerun()
  else:
    st.info("Conseil : Approchez ou éloignez doucement le code-barres du capteur pour aider la mise au point.")
