from sketch2code_pipeline import run_full_pipeline

if __name__ == "__main__":
    # Make sure this file exists in test_skteches/
    image_name = "uizard.png"

    result = run_full_pipeline(image_name)

    print("\n[PIPELINE DONE]")
    print("Input image:         ", result["input_image"])
    print("Preprocessed image:  ", result["preprocessed_image"])
    print("Text metadata JSON:  ", result["text_metadata_json"])
    print("YOLO outputs folder: ", result["yolo_output_dir"])

