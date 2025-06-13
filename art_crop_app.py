import streamlit as st
from PIL import Image
import cv2
import numpy as np
import io
import zipfile

st.set_page_config(page_title="Crop Artworks", layout="wide")
st.title("🎨 Crop Artworks from Multi-Image Uploads")

uploaded_files = st.file_uploader(
    "Upload multiple artwork sheets (TIFF/JPG/PNG)", 
    type=["tif", "tiff", "jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

MAX_PIXELS_SAFE = 100_000_000

if uploaded_files:
    tabs = st.tabs([f"{file.name}" for file in uploaded_files])

    for idx, uploaded_file in enumerate(uploaded_files):
        with tabs[idx]:
            st.subheader(f"📂 `{uploaded_file.name}`")
            pil_image = Image.open(uploaded_file)
            width, height = pil_image.size
            pixel_count = width * height

            if pixel_count > MAX_PIXELS_SAFE:
                st.error("❌ Image too large to process. Please reduce resolution.")
                continue

            if st.button(f"🚀 Process `{uploaded_file.name}`", key=f"btn_{idx}"):
                try:
                    image = pil_image.convert("RGB")
                    image_np = np.array(image)

                    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
                    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    zip_buffer = io.BytesIO()
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
                                zip_file.writestr(f"{uploaded_file.name}_artwork_{i+1}.jpg", img_bytes.getvalue())
                                previews.append((cropped_img, f"Artwork {i+1}"))

                    st.success(f"✅ Cropped {len(previews)} images.")
                    st.download_button(
                        label="⬇️ Download ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"{uploaded_file.name}_cropped.zip",
                        mime="application/zip"
                    )

                    st.subheader("🖼️ Preview All Cropped Images")
                    cols = st.columns(3)
                    for i, (img, label) in enumerate(previews):
                        with cols[i % 3]:
                            st.image(img, caption=label, use_container_width=True)

                except Exception as e:
                    st.error(f"⚠️ Error processing file: {e}")
