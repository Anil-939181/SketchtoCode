from ultralytics import YOLO
import os

# 1. Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assuming the user unzips the new dataset into this folder
DATA_YAML = os.path.join(BASE_DIR, "new_dataset", "data.yaml")

def train_model():
    if not os.path.exists(DATA_YAML):
        print(f"Error: Could not find dataset config at {DATA_YAML}.")
        print("Please download the YOLOv8 dataset from Roboflow/Kaggle, extract it,")
        print("and rename the folder to 'new_dataset' in the Sketch2Code directory.")
        return

    # Load a pretrained YOLOv8n model (Nano - fastest to train locally)
    model = YOLO("yolov8n.pt")
    
    # Optional: If you want to use the Small or Medium model for more accuracy:
    # model = YOLO("yolov8s.pt") 

    print("Starting YOLO Training...")
    # Train the model
    results = model.train(
        data=DATA_YAML,
        epochs=50,       # Start with 50 epochs
        imgsz=640,       # Image size 640x640 default
        batch=16,        # Batch size
        device="cpu",    # Change to "0" if you have an Nvidia GPU setup (CUDA)
        project="Enhanced_Model_Runs",
        name="sketch_detection",
        # Important Augmentations for hand-drawn sketches:
        degrees=15.0,    # Rotate by up to 15 degrees
        perspective=0.001,
        fliplr=0.0       # Do NOT flip left-right for UI elements (text becomes backwards)
    )
    
    print("Training Complete! The best model is saved in Enhanced_Model_Runs/sketch_detection/weights/best.pt")

if __name__ == "__main__":
    train_model()
