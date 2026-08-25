from get_svg_indicator import fetch_and_build_indicator

import av
import cv2
import queue
import re
import requests
import streamlit as st
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer
import base64
from IPython.display import SVG, display


camera_id = 0
delay = 1
window_name = 'OpenCV pyzbar'

cap = cv2.VideoCapture(camera_id)

while True:
    ret, frame = cap.read()

    if ret:
        for d in decode(frame):
            s = d.data.decode()
            print(s)
            frame = cv2.rectangle(frame, (d.rect.left, d.rect.top),
                                  (d.rect.left + d.rect.width, d.rect.top + d.rect.height), (0, 255, 0), 3)
            frame = cv2.putText(frame, s, (d.rect.left, d.rect.top + d.rect.height),
                                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2, cv2.LINE_AA)

            svg_code = fetch_and_build_indicator(s)
            display(SVG(svg_code))
        cv2.imshow(window_name, frame)

    if cv2.waitKey(delay) & 0xFF == ord('q'):
        break

cv2.destroyWindow(window_name)




#display(SVG(fetch_and_build_indicator(3850354016830)))







