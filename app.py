import av
import cv2
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

st.title("Scanner Code-Barres Ultra-Fluide")


class BarcodeProcessor(VideoProcessorBase):

  def __init__(self) -> None:
    self.found_code = None

  def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")

    # Conversion en nuances de gris pour optimiser pyzbar
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)

    for barcode in barcodes:
      self.found_code = barcode.data.decode("utf-8")

      # Dessine le rectangle vert
      (x, y, w, h) = barcode.rect
      cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)

    return av.VideoFrame.from_ndarray(img, format="bgr24")


# Lancement du flux WebRTC
ctx = webrtc_streamer(
    key="barcode-scanner-webrtc",
    video_processor_factory=BarcodeProcessor,
    rtc_configuration={"iceServers": [{"urls": ["stun:://google.com"]}]},
    media_stream_constraints={"video": {"facingMode": "environment"}, "audio": False},
)

# Lecture sécurisée du résultat pour éviter l'AttributeError
if ctx.video_processor:
  # Permet de récupérer l'attribut s'il existe, sinon renvoie None
  detected_code = getattr(ctx.video_processor, "found_code", None)

  if detected_code:
    st.success(f"Code-barres détecté : {detected_code}")
