import json
import os

def generate_responsive_html(merged_components, html_path):
    """
    Experimental: Converts bounding boxes into a responsive layout (Flexbox) 
    instead of absolute positioning by grouping elements into rows.
    """
    if not merged_components:
        print("No components to generate HTML.")
        return

    # Sort components top-to-bottom
    sorted_comps = sorted(merged_components, key=lambda c: c["bbox"][1])
    
    rows = []
    current_row = []
    row_y_threshold = 30  # pixels difference to be considered same row

    # Group into rows based on Y coordinate
    for comp in sorted_comps:
        if not current_row:
            current_row.append(comp)
        else:
            # Check if this component is vertically close to the current row's average Y
            avg_y = sum(c["bbox"][1] for c in current_row) / len(current_row)
            if abs(comp["bbox"][1] - avg_y) < row_y_threshold:
                current_row.append(comp)
            else:
                rows.append(current_row)
                current_row = [comp]
    
    if current_row:
        rows.append(current_row)

    # Now generate responsive HTML
    html_elements = []
    
    for row in rows:
        # Sort left-to-right within the row
        row = sorted(row, key=lambda c: c["bbox"][0])
        
        row_html = '<div style="display: flex; flex-direction: row; align-items: center; justify-content: flex-start; gap: 15px; margin-bottom: 20px; width: 100%;">'
        
        for comp in row:
            text = comp.get("text", "") or ""
            ui_type = (comp.get("ui_type", "") or "").lower()
            text_type = (comp.get("text_type", "") or "").lower()
            
            # Base style for the element
            style = "padding: 10px; font-family: sans-serif;"
            
            if ui_type == "button" or "button" in text_type:
                element = f'<button style="{style} cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px;">{text if text else "Button"}</button>'
            elif ui_type in ["textbox", "input", "input_field"]:
                placeholder = text if text_type in ["form_label", "label", "placeholder"] else "Input..."
                element = f'<input type="text" style="{style} border: 1px solid #ccc; border-radius: 4px;" placeholder="{placeholder}"/>'
            elif text_type in ["heading", "navbar_text"]:
                element = f'<h2 style="{style} margin: 0;">{text}</h2>'
            elif text_type in ["subheading"]:
                element = f'<h3 style="{style} margin: 0;">{text}</h3>'
            elif text_type in ["paragraph", "footer_text"]:
                element = f'<p style="{style} margin: 0;">{text}</p>'
            elif ui_type == "image":
                element = f'<div style="{style} background: #eee; border: 1px dashed #aaa; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center;">Image</div>'
            else:
                element = f'<span style="{style} color: #333;">{text if text else ui_type}</span>'
                
            row_html += f'\n    {element}'
            
        row_html += '\n  </div>'
        html_elements.append(row_html)

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Responsive Sketch2Code</title>
  <style>
    body {{
      margin: 0;
      padding: 40px;
      font-family: Arial, sans-serif;
      background-color: #f9f9f9;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
  </style>
</head>
<body>
  <div class="container">
    {''.join(html_elements)}
  </div>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_page)

    print(f"[HTML] Responsive Layout Saved to: {html_path}")

# Example usage (you would call this from your main file):
# generate_responsive_html(merged_json_data, "output_responsive.html")
