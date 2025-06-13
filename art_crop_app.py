import streamlit as st
from PIL import Image
import cv2
import numpy as np
import io
import zipfile
import traceback
import sys

st.set_page_config(page_title="Safe Auto-Crop Artworks", layout="wide")
st.title("🖼️ Auto-Crop Artworks (with Labels)")

uploaded_files = st.file_uploader(
    "Upload TIFF/JPG/PNG files (Max ~70 Megapixels per image)", 
    type=["tif", "tiff", "jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

MAX_PIXELS_SAFE = 70_000_000  # 70 MP safe on Streamlit Cloud

if uploaded_files:
    tabs = st.tabs([f"{f.name}" for f in uploaded_files])

    for idx, uploaded_file in enumerate(uploaded_files):
        with tabs[idx]:
            try:
                st.subheader(f"📂 `{uploaded_file.name}`")

                # Load metadata only first
                pil_image = Image.open(uploaded_file)
                width, height = pil_image.size
                pixel_count = width * height

                if pixel_count > MAX_PIXELS_SAFE:
                    st.error(f"🚫 Image too large to safely process ({width} x {height} = {pixel_count // 1_000_000}MP).\nPlease upload this file separately after resizing.")
                    continue

                image = pil_image.convert("RGB")
                image_np = np.asarray(image)  # Now convert only after passing checks

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

                            if valid_count < 12:  # Prevent too many previews
                                previews.append((cropped_img, f"Artwork {valid_count + 1}"))

                            valid_count += 1

                if valid_count > 0:
                    st.success(f"✅ {valid_count} artworks cropped.")
                    st.download_button(
                        label=f"⬇️ Download ZIP for `{uploaded_file.name}`",
                        data=zip_buffer.getvalue(),
                        file_name=f"{uploaded_file.name}_cropped_artworks.zip",
                        mime="application/zip"
                    )
                    if previews:
                        with st.expander("🖼️ Preview First 12 Artworks"):
                            cols = st.columns(3)
                            for i, (img, label) in enumerate(previews):
                                with cols[i % 3]:
                                    st.image(img, caption=label, use_container_width=True)
                else:
                    st.warning("⚠️ No valid artworks found.")
            except Exception as e:
                st.error(f"❌ Could not process `{uploaded_file.name}`")
                st.text(''.join(traceback.format_exception(*sys.exc_info())))
