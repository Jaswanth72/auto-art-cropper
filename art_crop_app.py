import streamlit as st
from PIL import Image
import cv2
import numpy as np
import io
import zipfile

st.set_page_config(page_title="Batch Auto-Crop Artworks", layout="wide")
st.title("🖼️ Batch Auto-Crop Artworks (with Labels)")

uploaded_files = st.file_uploader(
    "Upload multiple TIFF/JPG/PNG files", 
    type=["tif", "tiff", "jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

if uploaded_files:
    tabs = st.tabs([f"{f.name}" for f in uploaded_files])

    for idx, uploaded_file in enumerate(uploaded_files):
        with tabs[idx]:
            try:
                st.subheader(f"📂 `{uploaded_file.name}`")
                
                # Load and optionally resize large image
                image = Image.open(uploaded_file).convert("RGB")
                max_dimension = 2000
                if max(image.size) > max_dimension:
                    image.thumbnail((max_dimension, max_dimension))

                image_np = np.array(image)

                gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                zip_buffer = io.BytesIO()
                valid_count = 0
                thumbnails = []

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

                            thumbnails.append((cropped_img, f"Artwork {valid_count + 1}"))

                            img_bytes = io.BytesIO()
                            cropped_img.save(img_bytes, format='JPEG')
                            zip_file.writestr(f"{uploaded_file.name}_artwork_{valid_count + 1}.jpg", img_bytes.getvalue())
                            valid_count += 1

                if valid_count > 0:
                    st.success(f"✅ Detected {valid_count} artworks")
                    st.download_button(
                        label=f"⬇️ Download ZIP for `{uploaded_file.name}`",
                        data=zip_buffer.getvalue(),
                        file_name=f"{uploaded_file.name}_cropped_artworks.zip",
                        mime="application/zip"
                    )
                    with st.expander("🖼️ Preview Cropped Artworks"):
                        cols = st.columns(3)
                        for i, (img, label) in enumerate(thumbnails):
                            with cols[i % 3]:
                                st.image(img, caption=label, use_container_width=True)
                else:
                    st.warning(f"⚠️ No valid artworks detected in `{uploaded_file.name}`.")
            except Exception as e:
                st.error(f"❌ Failed to process `{uploaded_file.name}`:\n\n{e}")
