from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from gemini_service import generate_code_from_image

app = FastAPI(title="Gemini Sketch2Code")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r") as f:
        return f.read()

import sys
import os
from pathlib import Path

# Add parent directory to sys.path to import sketch2code_pipeline
parent_dir = str(Path(__file__).parent.parent.absolute())
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from sketch2code_pipeline import (
    preprocess_ui_image, 
    extract_text_metadata_combined,
    run_yolo_detection,
    load_yolo_model,
    TEST_SKETCHES_DIR,
    MODEL_PATH
)

@app.post("/api/generate")
async def generate_code(
    image: UploadFile = File(...),
    framework: str = Form(...)
):
    try:
        contents = await image.read()
        
        import uuid
        os.makedirs(TEST_SKETCHES_DIR, exist_ok=True)
        temp_filename = f"temp_upload_{uuid.uuid4().hex}.png"
        temp_filepath = os.path.join(TEST_SKETCHES_DIR, temp_filename)
        
        with open(temp_filepath, "wb") as f:
            f.write(contents)
        
        # Run pipeline with step tracking
        try:
            # Step 1: Preprocessing
            print(f"[STEP] preprocessing starting")
            preprocessed_path, text_boxes = preprocess_ui_image(
                image_path=temp_filepath,
                show=False
            )
            print(f"[STEP] preprocessing completed")
            
            # Step 2: Text Extraction
            print(f"[STEP] text_extraction starting")
            text_blocks, metadata_json_path = extract_text_metadata_combined(
                image_path=temp_filepath,
                show=False
            )
            print(f"[STEP] text_extraction completed")
            
            # Step 3: Element Detection
            print(f"[STEP] detection starting")
            model = load_yolo_model(MODEL_PATH)
            detections, yolo_save_dir = run_yolo_detection(
                image_path=temp_filepath,
                model=model
            )
            print(f"[STEP] detection completed")
            
        except Exception as e:
            print(f"Error executing custom pipeline: {e}")
            import traceback
            traceback.print_exc()

        # Step 4: Code Generation (via Gemini)
        print(f"[STEP] code_generation starting")
        code_result = generate_code_from_image(contents, framework)
        print(f"[STEP] code_generation completed")
        
        return {"code": code_result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
