import os
from dotenv import load_dotenv
from google import genai

# 1. Force Python to load variables from the .env file in the same directory
load_dotenv()

# 2. Securely fetch the API key
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not found. Please check your .env file.")

# 3. Initialize the NEW Client syntax
client = genai.Client(api_key=api_key)

def check_supported_models():
    print("Fetching available Gemini models using the new SDK...\n")
    
    total_models = 0
    flash_available = False
    
    # 4. Use the new client.models.list() generator
    for model in client.models.list():
        total_models += 1
        print(f"Model ID: {model.name}")
        print(f"Display Name: {model.display_name}")
        print(f"Description: {model.description}")
        print("-" * 50)
        
        # Check if your specific model is in the list
        if "gemini-2.5-flash" in model.name:
            flash_available = True
            
    print(f"\n✅ Total models returned by API: {total_models}")
    print(f"✅ System check for gemini-2.5-flash: {'ONLINE' if flash_available else 'NOT FOUND'}")
    
    print("\nAttempting to generate 1 word of text to test Quota limitations...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Say the word "test".'
        )
        print(f"✅ SUCCESS! Response: {response.text}")
    except Exception as e:
        print(f"❌ GENERATION BLOCKED: {e}")

if __name__ == "__main__":
    check_supported_models()