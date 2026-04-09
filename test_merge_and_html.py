import json
import os
import math

# ========== CONFIG: SET YOUR FILE PATHS HERE ==========

# Example:
# metadata_json = r"metadata jsion\uizard_text_metadata.json"
# detections_json = r"sketch2code_prediction\uizard\detection_details.json"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

METADATA_JSON = os.path.join(BASE_DIR, r"test_images_metadata_json", "form_text_metadata.json")
DETECTIONS_JSON = os.path.join(BASE_DIR, r"Sketch2Code_Predictions", "form", "detection_details.json")

OUTPUT_DIR = os.path.join(BASE_DIR, "generated_code")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "uizard_generated.html")
OUTPUT_MERGED_JSON = os.path.join(OUTPUT_DIR, "uizard_merged_components.json")


# ========== HELPERS ==========

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h

    if inter_area == 0:
        return 0.0

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    union_area = boxA_area + boxB_area - inter_area

    return inter_area / (union_area + 1e-6)

def center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


# ========== 1. MERGE ==========

def merge_metadata_and_detections(metadata_json_path, detection_json_path):
    text_blocks = load_json(metadata_json_path)      # list of dicts
    detections = load_json(detection_json_path)     # list of dicts

    # prepare text items with match flags
    text_items = []
    for idx, tb in enumerate(text_blocks):
        x1, y1, x2, y2 = tb["coordinates"]
        text_items.append({
            "index": idx,
            "bbox": [float(x1), float(y1), float(x2), float(y2)],
            "text": tb["text"],
            "text_type": tb["type"],
            "meta": tb,
            "matched": False,
        })

    merged_components = []
    comp_id = 1

    # for each detection, find best matching text
    for det_index, det in enumerate(detections):
        det_box = [float(det["x1"]), float(det["y1"]), float(det["x2"]), float(det["y2"])]

        best_text_item = None
        best_score = 0.0

        for t in text_items:
            txt_box = t["bbox"]
            overlap = iou(det_box, txt_box)

            if overlap > 0:
                score = 1.0 + overlap  # overlapping gets high priority
            else:
                cx_d, cy_d = center(det_box)
                cx_t, cy_t = center(txt_box)
                dist = math.dist((cx_d, cy_d), (cx_t, cy_t))
                score = 1.0 / (1.0 + dist)  # closer → higher

            if score > best_score:
                best_score = score
                best_text_item = t

        # You can add a threshold if you want; for now we always attach best_text_item
        attached_text = ""
        attached_text_type = None
        text_index = None
        text_meta = None

        if best_text_item is not None:
            best_text_item["matched"] = True
            attached_text = best_text_item["text"]
            attached_text_type = best_text_item["text_type"]
            text_index = best_text_item["index"]
            text_meta = best_text_item["meta"]

        width = float(det.get("width", det_box[2] - det_box[0]))
        height = float(det.get("height", det_box[3] - det_box[1]))

        merged_components.append({
            "id": comp_id,
            "ui_type": det["class_name"],
            "text": attached_text,
            "text_type": attached_text_type,
            "bbox": det_box,
            "width": width,
            "height": height,
            "ui_confidence": det.get("confidence", None),
            "source": {
                "detection_index": det_index,
                "text_index": text_index
            },
            "text_meta": text_meta
        })

        comp_id += 1

    # add text-only blocks
    for t in text_items:
        if not t["matched"]:
            x1, y1, x2, y2 = t["bbox"]
            merged_components.append({
                "id": comp_id,
                "ui_type": "text_only",
                "text": t["text"],
                "text_type": t["text_type"],
                "bbox": t["bbox"],
                "width": x2 - x1,
                "height": y2 - y1,
                "ui_confidence": None,
                "source": {
                    "detection_index": None,
                    "text_index": t["index"]
                },
                "text_meta": t["meta"]
            })
            comp_id += 1

    return merged_components


# ========== 2. DOM TREE & HTML GENERATION ==========

def build_dom_tree(components):
    # Sort components by area, descending (largest first)
    # This helps ensure containers are processed before their children
    sorted_comps = sorted(
        components,
        key=lambda c: c["width"] * c["height"],
        reverse=True
    )
    
    # Initialize children array for all
    for c in sorted_comps:
        c["children"] = []
        c["parent_id"] = None

    root_elements = []

    for i, child_comp in enumerate(sorted_comps):
        cx1, cy1, cx2, cy2 = child_comp["bbox"]
        child_area = child_comp["width"] * child_comp["height"]
        
        # Find the smallest parent that contains this child
        best_parent = None
        best_parent_area = float('inf')
        
        for j, parent_comp in enumerate(sorted_comps):
            if i == j: continue
            
            px1, py1, px2, py2 = parent_comp["bbox"]
            parent_area = parent_comp["width"] * parent_comp["height"]
            
            # Check if child is mostly inside parent (e.g. at least 60% of child is inside parent)
            inter_x1 = max(cx1, px1)
            inter_y1 = max(cy1, py1)
            inter_x2 = min(cx2, px2)
            inter_y2 = min(cy2, py2)
            
            if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                if inter_area > 0.6 * child_area and parent_area > child_area:
                    if parent_area < best_parent_area:
                        best_parent = parent_comp
                        best_parent_area = parent_area
        
        if best_parent:
            child_comp["parent_id"] = best_parent["id"]
            best_parent["children"].append(child_comp)
        else:
            root_elements.append(child_comp)

    # Sort children left-to-right, top-to-bottom
    def sort_children(node):
        node["children"].sort(key=lambda c: (c["bbox"][1] // 20, c["bbox"][0]))
        for child in node["children"]:
            sort_children(child)
            
    for root in root_elements:
        sort_children(root)

    return root_elements

def render_html_node(node):
    ui_type = str(node.get("ui_type", "")).lower()
    text = node.get("text", "")
    text_type = str(node.get("text_type", "")).lower()
    
    # Apply flex layout if it has children
    style = "margin: 8px;"
    if node["children"]:
        style += " display: flex; flex-wrap: wrap; align-items: center; gap: 10px; border: 1px dotted #ccc; padding: 10px;"
        
    children_html = "".join([render_html_node(c) for c in node["children"]])
    
    # Base Element Routing
    if ui_type == "button" or "button" in text_type:
        return f'<button style="{style} padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">{text if text else "Button"}{children_html}</button>'
    
    elif ui_type in ["textbox", "input", "input_field"]:
        placeholder = text if text_type in ["form_label", "label", "placeholder"] else ""
        return f'<input type="text" style="{style} padding: 8px; border: 1px solid #ccc; border-radius: 4px;" placeholder="{placeholder}"/>'
        
    elif ui_type == "checkbox":
        return f'<label style="{style} display: flex; align-items: center; gap: 5px;"><input type="checkbox"/> {text if text else ""}{children_html}</label>'
        
    elif ui_type == "radiobutton":
        return f'<label style="{style} display: flex; align-items: center; gap: 5px;"><input type="radio" name="radio_group"/> {text if text else ""}{children_html}</label>'

    elif ui_type == "switch":
        return f'<div style="{style} display: flex; align-items: center; gap: 5px;"><input type="checkbox" role="switch"/> {text if text else "Switch"}{children_html}</div>'

    elif ui_type == "image":
        return f'<div style="{style} width: 100px; height: 100px; background: #eee; border: 1px dashed #aaa; display: flex; justify-content: center; align-items: center;">{text if text else "Image"}{children_html}</div>'
        
    elif text_type in ["heading", "title", "navbar_text"]:
        return f'<h2 style="{style} margin: 0;">{text}{children_html}</h2>'
        
    elif text_type in ["subheading"]:
        return f'<h3 style="{style} margin: 0;">{text}{children_html}</h3>'
        
    elif text_type in ["paragraph", "footer_text"]:
        return f'<p style="{style} margin: 0;">{text}{children_html}</p>'
        
    elif text or children_html:
        return f'<div style="{style}">{text}{children_html}</div>'
        
    else:
        return f'<div style="{style} height: 50px; width: 100px; border: 1px solid #ccc;">{ui_type}</div>'

def generate_html_from_components(merged_components, html_path):
    if not merged_components:
        raise ValueError("merged_components is empty")

    root_nodes = build_dom_tree(merged_components)
    root_nodes.sort(key=lambda c: (c["bbox"][1] // 30, c["bbox"][0])) # Sort top level items
    
    html_elements = [render_html_node(node) for node in root_nodes]

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sketch2Code Responsive UI (Flexbox Nested DOM)</title>
  <style>
    body {{
      margin: 0;
      padding: 40px;
      font-family: system-ui, -apple-system, sans-serif;
      background-color: #f4f4f5;
    }}
    .canvas {{
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
      display: flex;
      flex-direction: column;
      gap: 15px;
    }}
  </style>
</head>
<body>
  <div class="canvas">
    {''.join(html_elements)}
  </div>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_page)

    print(f"[HTML] Responsive DOM Tree HTML Saved: {html_path}")


# ========== MAIN ==========

if __name__ == "__main__":
    print("[INFO] Using metadata:", METADATA_JSON)
    print("[INFO] Using detections:", DETECTIONS_JSON)

    merged = merge_metadata_and_detections(METADATA_JSON, DETECTIONS_JSON)

    with open(OUTPUT_MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"[MERGE] Merged components saved to: {OUTPUT_MERGED_JSON}")
    print(f"[MERGE] Total components: {len(merged)}")

    generate_html_from_components(merged, OUTPUT_HTML)

