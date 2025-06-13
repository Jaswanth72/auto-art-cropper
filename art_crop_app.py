import streamlit as st
from PIL import Image
import cv2
import numpy as np
import io
import zipfile
import traceback
import sys

st.set_page_config(page_title="Auto-Crop Artworks", layout="wide")
st.title("🖼️ Auto-Crop One Artwork Sheet at a Time")

uploaded_file = st.file_uploader(
    "Upload one TIFF/JPG/PNG file", 
    type=["tif", "tiff", "jpg", "jpeg", "png"]
)

MAX_PIXELS_SAFE = 100_000_000  # 100MP safety check

if uploaded_file:
    try:
        st.subheader(f"📂 `{uploaded_file.name}`")

        pil_image = Image.open(uploaded_file)
        width, height = pil_image.size
        pixel_count = width * height

        if pixel_count > MAX_PIXELS_SAFE:
            st.error(f"🚫 Image too large to safely process ({width} x {height} = {pixel_count // 1_000_000}MP). Please reduce resolution.")
        else:
            image = pil_image.convert("RGB")
            image_np = np.array(image)

            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            zip_buffer = io.BytesIO()
            valid_count = 0
            previews = []

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                for i, contour in enumerate(contours):
                    x, y, w, h = cv2.boundingRect(contour)
                    area = cv2.contourArea(contour)
                    aspect_ratio = w / h if h != 0 else 0

                    if area > 5000 and 0.5 < aspect_ratio < 2.5 and w > 100 and h > 100:
                        extended_h = int(h * 1.2)
                        y_end = min(y + extended_h, image_np.shape[0])
                        cropped = image_np[y:y_end, x:x+w]
                        cropped_img = Image.fromarray(cropped)

                        img_bytes = io.BytesIO()
                        cropped_img.save(img_bytes, format='JPEG', quality=95)
                        zip_file.writestr(f"{uploaded_file.name}_artwork_{valid_count + 1}.jpg", img_bytes.getvalue())

                        if valid_count < 12:
                            previews.append((cropped_img, f"Artwork {valid_count + 1}"))

                        valid_count += 1

            if valid_count > 0:
                st.success(f"✅ {valid_count} artworks cropped.")
                st.download_button(
                    label="⬇️ Download Cropped ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"{uploaded_file.name}_cropped.zip",
                    mime="application/zip"
                )
                with st.expander("🖼️ Preview First 12 Crops"):
                    cols = st.columns(3)
                    for i, (img, label) in enumerate(previews):
                        with cols[i % 3]:
                            st.image(img, caption=label, use_container_width=True)
            else:
                st.warning("⚠️ No valid artworks found.")

    except Exception as e:
        st.error(f"❌ Could not process `{uploaded_file.name}`")
        st.text(''.join(traceback.format_exception(*sys.exc_info())))
