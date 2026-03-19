import google.generativeai as genai

genai.configure(api_key="AIzaSyAPrJCPFz8SdFXTSqaKqzKvp0QYqKfXnzk")

for m in genai.list_models():
    print(m.name, m.supported_generation_methods)