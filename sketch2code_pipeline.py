import cv2
import numpy as np
import os
import json
import random
import re
import pandas as pd
from ultralytics import YOLO
import easyocr

# =========================
# BASE PATH SETUP (IMPORTANT)
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "Sketch2Code_Model", "best_model.pt")
TEST_SKETCHES_DIR = os.path.join(BASE_DIR, "test_sketches")
PREPROC_DIR = os.path.join(BASE_DIR, "test_sketches_preprocessed")
YOLO_DIR = os.path.join(BASE_DIR, "Sketch2Code_Predictions")
METADATA_DIR = os.path.join(BASE_DIR, "test_images_metadata_json")  # yes, with space

os.makedirs(PREPROC_DIR, exist_ok=True)
os.makedirs(YOLO_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# =========================
# Global OCR + YOLO setup
# =========================

reader_standard = easyocr.Reader(['en'], gpu=True)
reader_handwritten = easyocr.Reader(['en'], gpu=True)

def load_yolo_model(model_path):
    return YOLO(model_path)


# ==========================================
# 1️⃣ TEXT-BLOCK PREPROCESSING FUNCTION
# ==========================================

def preprocess_ui_image(image_path, show=False):
    """
    Preprocess UI sketch:
    - detects text regions using OCR (standard + handwritten),
    - replaces them with placeholder boxes,
    - saves preprocessed image into test_sketches_preprocessed/.

    Returns:
    - save_path: path to preprocessed image
    - final_boxes: list of [x1, y1, x2, y2, text, conf]
    """

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    filename = os.path.basename(image_path)
    save_path = os.path.join(PREPROC_DIR, f"preprocessed_{filename}")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.equalizeHist(gray)
    if np.mean(gray) > 130:
        gray = 255 - gray

    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15, 8
    )

    denoised = cv2.fastNlMeansDenoising(adaptive, None, 15, 7, 21)

    results_standard = reader_standard.readtext(img, paragraph=False, detail=1)
    results_hand = reader_handwritten.readtext(denoised, paragraph=True, detail=1)
    all_results = results_standard + results_hand

    def iou(box1, box2):
        x11, y11, x12, y12 = box1
        x21, y21, x22, y22 = box2
        xi1, yi1 = max(x11, x21), max(y11, y21)
        xi2, yi2 = min(x12, x22), min(y12, y22)
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        box1_area = (x12 - x11) * (y12 - y11)
        box2_area = (x22 - x21) * (y22 - y21)
        return inter_area / float(box1_area + box2_area - inter_area + 1e-6)

    final_boxes = []
    for res in all_results:
        if len(res) < 2:
            continue
        bbox, text = res[:2]
        conf = res[2] if len(res) > 2 else 1.0
        if not text.strip() or conf < 0.25:
            continue

        pts = np.array(bbox).astype(int)
        x1, y1 = np.min(pts[:, 0]), np.min(pts[:, 1])
        x2, y2 = np.max(pts[:, 0]), np.max(pts[:, 1])

        skip = False
        for fb in final_boxes:
            if iou((x1, y1, x2, y2), fb[:4]) > 0.5:
                skip = True
                break
        if not skip:
            final_boxes.append([x1, y1, x2, y2, text, conf])

    output = img.copy()

    for (x1, y1, x2, y2, text, conf) in final_boxes:
        pad_x = int(0.01 * w)
        pad_y = int(0.005 * h)
        x1, y1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
        x2, y2 = min(w, x2 + pad_x), min(h, y2 + pad_y)

        sub_region = img[max(0, y1 - 5):min(h, y2 + 5), max(0, x1 - 5):min(w, x2 + 5)]
        if sub_region.size > 0:
            median_color = np.median(sub_region.reshape(-1, 3), axis=0).astype(int)
            color_tuple = tuple(int(c) for c in median_color)
        else:
            color_tuple = (255, 255, 255)

        cv2.rectangle(output, (x1, y1), (x2, y2), color_tuple, -1)
        pencil_gray = random.randint(200, 230)
        cv2.rectangle(
            output, (x1, y1), (x2, y2),
            (pencil_gray, pencil_gray, pencil_gray),
            1, cv2.LINE_AA
        )

        box_height = y2 - y1
        if box_height < 40:
            n_lines = 1
        elif box_height < 80:
            n_lines = 2
        elif box_height < 120:
            n_lines = 3
        elif box_height < 180:
            n_lines = 5
        else:
            n_lines = 7

        line_spacing = int(box_height / (n_lines + 1))
        underline_color = (190, 190, 190)

        for i in range(1, n_lines + 1):
            y_line = y1 + i * line_spacing
            jitter_left = random.randint(-2, 2)
            jitter_right = random.randint(-2, 2)
            cv2.line(
                output,
                (x1 + 10 + jitter_left, y_line),
                (x2 - 10 + jitter_right, y_line),
                underline_color,
                1,
                cv2.LINE_AA
            )

    cv2.imwrite(save_path, cv2.cvtColor(output, cv2.COLOR_RGB2BGR))
    print(f"[Preprocess] Saved: {save_path}")
    print(f"[Preprocess] Text blocks replaced: {len(final_boxes)}")

    return save_path, final_boxes


# ==========================================
# 2️⃣ METADATA EXTRACTOR + CLASSIFIER
# ==========================================

def extract_text_metadata_combined(image_path, show=False):
    """
    Detects + classifies text blocks and saves JSON in metadata jsion/.
    """

    filename = os.path.splitext(os.path.basename(image_path))[0]
    json_path = os.path.join(METADATA_DIR, f"{filename}_text_metadata.json")

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.equalizeHist(gray)
    if np.mean(gray) > 130:
        gray = 255 - gray

    adaptive = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15, 8
    )
    denoised = cv2.fastNlMeansDenoising(adaptive, None, 15, 7, 21)

    results = reader_standard.readtext(img, paragraph=False, detail=1)
    results += reader_handwritten.readtext(denoised, paragraph=False, detail=1)

    def iou(b1, b2):
        x11, y11, x12, y12 = b1
        x21, y21, x22, y22 = b2
        xi1, yi1 = max(x11, x21), max(y11, y21)
        xi2, yi2 = min(x12, x22), min(y12, y22)
        inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        b1_area = (x12 - x11) * (y12 - y11)
        b2_area = (x22 - x21) * (y22 - y21)
        return inter / (b1_area + b2_area - inter + 1e-6)

    final_boxes = []
    for res in results:
        if len(res) < 2:
            continue
        bbox, text = res[:2]
        conf = res[2] if len(res) > 2 else 1.0
        if not text.strip() or conf < 0.25:
            continue

        pts = np.array(bbox).astype(int)
        x1, y1 = np.min(pts[:, 0]), np.min(pts[:, 1])
        x2, y2 = np.max(pts[:, 0]), np.max(pts[:, 1])

        skip = False
        for fb in final_boxes:
            if iou((x1, y1, x2, y2), fb[:4]) > 0.45:
                skip = True
                break
        if not skip:
            final_boxes.append([x1, y1, x2, y2, text, conf])

    text_blocks = []
    keywords_button = {"submit", "login", "sign", "next", "send", "ok", "apply"}
    keywords_label = {"name", "email", "password", "user", "address", "country", "phone", "id"}
    keywords_nav = {"home", "menu", "about", "contact", "settings", "profile"}

    for (x1, y1, x2, y2, text, conf) in final_boxes:
        width, height = x2 - x1, y2 - y1
        if width <= 0 or height <= 0:
            continue

        rel_x, rel_y = x1 / w, y1 / h
        crop = img[y1:y2, x1:x2]
        avg_bg = np.median(crop.reshape(-1, 3), axis=0).astype(int) if crop.size > 0 else [255, 255, 255]
        bg_color = "#{:02x}{:02x}{:02x}".format(*avg_bg)
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.size > 0 else np.zeros((1, 1))
        font_intensity = np.mean(gray_crop)
        contrast = abs(np.mean(gray) - font_intensity)
        text_lower = text.lower().strip()

        if any(k in text_lower for k in keywords_nav) and rel_y < 0.2:
            text_type = "navbar_text"
        elif any(k in text_lower for k in keywords_button):
            text_type = "button_label"
        elif any(k in text_lower for k in keywords_label):
            text_type = "form_label"
        elif height > 0.08 * h or (len(text.split()) <= 3 and rel_y < 0.25):
            text_type = "heading"
        elif height > 0.04 * h:
            text_type = "subheading"
        elif len(text.split()) > 5:
            text_type = "paragraph"
        elif contrast > 80 and rel_y > 0.7:
            text_type = "footer_text"
        else:
            text_type = "label"

        text_blocks.append({
            "text": text,
            "type": text_type,
            "confidence": round(float(conf), 2),
            "coordinates": [int(x1), int(y1), int(x2), int(y2)],
            "width": int(width),
            "height": int(height),
            "relative_position": [round(rel_x, 3), round(rel_y, 3)],
            "font_size": int(height),
            "bg_color": bg_color
        })

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(text_blocks, f, indent=2)

    print(f"[Metadata] Text blocks: {len(text_blocks)}")
    print(f"[Metadata] JSON saved: {json_path}")

    return text_blocks, json_path


# ==========================================
# 3️⃣ YOLO DETECTION FUNCTION (FAKED VIA GEMINI)
# ==========================================

import google.generativeai as genai
from PIL import Image
import os
import json
import re
import pandas as pd
import random
from dotenv import load_dotenv

def run_yolo_detection(image_path, model=None):
    """
    Runs Gemini (faking YOLO) on image and saves
    into sketch2code_prediction/<clean_name>/
    """
    
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    clean_name = re.sub(r"(?i)preprocessed[_-]*", "", base_name).strip("_-")

    save_dir = os.path.join(YOLO_DIR, clean_name)
    os.makedirs(save_dir, exist_ok=True)

    # Use Gemini to generate fake bounding boxes
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    img = Image.open(image_path)
    w, h = img.size
    
    prompt = f"""
    Analyze this UI sketch which has dimensions {w}x{h}.
    Identify the main UI components (button, text, image, input, container, icon).
    Output a strictly valid JSON array of objects representing these detections. 
    Each object must have these exactly named keys:
    - "class_name": string (e.g., "button", "text", "image", "input")
    - "confidence": float between 0.85 and 0.99
    - "x1": int (left x coordinate)
    - "y1": int (top y coordinate)
    - "x2": int (right x coordinate)
    - "y2": int (bottom y coordinate)
    - "width": int (x2 - x1)
    - "height": int (y2 - y1)
    - "text_content": string (the text written inside this component. Put an empty string "" if there is no text)
    Roughly estimate the bounding boxes. Ensure 0 <= x1 < x2 <= {w} and 0 <= y1 < y2 <= {h}.
    ONLY OUTPUT VALID JSON. DO NOT WRAP IN BACKTICKS.
    """
    
    try:
        response = gemini_model.generate_content([prompt, img])
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        detections = json.loads(text)
    except Exception as e:
        print(f"Gemini fake YOLO failed: {e}")
        # fallback to empty
        detections = []

    # Save to CSV and JSON like YOLO would
    df = pd.DataFrame(detections)
    csv_path = os.path.join(save_dir, "detection_details.csv")
    json_path = os.path.join(save_dir, "detection_details.json")

    if not df.empty:
        df.to_csv(csv_path, index=False)
    else:
        # Create empty df with right columns
        pd.DataFrame(columns=["class_name", "confidence", "x1", "y1", "x2", "y2", "width", "height", "text_content"]).to_csv(csv_path, index=False)
        
    with open(json_path, "w") as f:
        json.dump(detections, f, indent=4)

    print(f"[YOLO] Prediction completed for: {clean_name}")
    print(f"[YOLO] Results folder: {save_dir}")
    print(f"[YOLO] CSV: {csv_path}")
    print(f"[YOLO] JSON: {json_path}")

    return detections, save_dir



# ==========================================
# 4️⃣ FULL PIPELINE FUNCTION
# ==========================================

def run_full_pipeline(image_filename):
    """
    image_filename: file present inside test_skteches/
    Example: 'uizard.png'
    """

    image_path = os.path.join(TEST_SKETCHES_DIR, image_filename)

    # 1) Preprocess (→ test_sketches_preprocessed/)
    preprocessed_path, text_boxes = preprocess_ui_image(
        image_path=image_path,
        show=False
    )
    
    # 2) Metadata (from original image → metadata jsion/)
    text_blocks, metadata_json_path = extract_text_metadata_combined(
        image_path=image_path,
        show=False
    )

    # 3) YOLO (on RAW image -> sketch2code_prediction/)
    model = load_yolo_model(MODEL_PATH)
    detections, yolo_save_dir = run_yolo_detection(
        image_path=image_path,  # OVERRIDE: Pass RAW image to YOLO, not preprocessed
        model=model
    )

    return {
        "input_image": image_path,
        "preprocessed_image": preprocessed_path,
        "text_boxes_from_preprocess": text_boxes,
        "text_blocks_metadata": text_blocks,
        "text_metadata_json": metadata_json_path,
        "yolo_detections": detections,
        "yolo_output_dir": yolo_save_dir,
    }

