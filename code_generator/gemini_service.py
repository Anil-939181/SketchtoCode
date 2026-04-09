import os
from dotenv import load_dotenv

# Load before any other imports
load_dotenv()

import google.generativeai as genai
from PIL import Image
import io

print("Env variable ", os.environ.get("GEMINI_API_KEY"))

def configure_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running the app. Try: export GEMINI_API_KEY=your_key")
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
You are an expert Frontend Developer and UI/UX Designer.
I will provide you with a hand-drawn sketch, wireframe, or screenshot of a user interface, and I want you to convert it into functional code.
The requested framework or technology stack will be provided along with the image.

Your task:
1. Carefully analyze the layout, UI elements (buttons, inputs, headers, text, images, containers), text, and styling implied by the drawing.
2. Generate clean, valid, and responsive code strictly conforming to the requested framework (e.g., React, HTML/Tailwind, Vue, Angular, Streamlit).
3. STRICT STRUCTURAL AND VISUAL ADHERENCE: You must perfectly match the exact colors, layout, and styling present in the sketch. Do NOT add extra colors, "vibrant" embellishments, or styles that are not explicitly drawn or implied by the provided image. If the sketch is black and white or grayscale, the generated UI should also be black and white or grayscale. Write modern, fully functional code without using generic placeholders unless entirely necessary.
4. Provide a complete, runnable snippet wherever possible. If multiple files are needed, output them clearly separated, but prioritize single-file runnable examples if feasible.
5. Output MUST just be the code. Don't add conversational text. Output ONLY the raw markdown code block(s).
"""

def generate_code_from_image(image_bytes: bytes, framework: str) -> str:
    configure_gemini()
    
    # Using 2.5 flash for speed and multimodal capabilities
    import google.generativeai as genai
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    image = Image.open(io.BytesIO(image_bytes))
    
    prompt = f"{SYSTEM_PROMPT}\n\nThe user intends to build this UI using the following framework/technology: {framework}\n\nPlease generate the corresponding code."
    
    response = model.generate_content([prompt, image])
    return response.text
