import os
from dotenv import load_dotenv
from openai import OpenAI

# Force reload environment variables
load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")

print("=== OpenAI API Key Test ===\n")
print(f"API Key loaded: {api_key[:20]}...{api_key[-10:] if api_key else 'None'}")
print(f"API Key length: {len(api_key) if api_key else 0}")
print(f"Has whitespace: {api_key != api_key.strip() if api_key else 'N/A'}")

# Test the API key
try:
    client = OpenAI(api_key=api_key.strip() if api_key else None)
    
    print("\nTesting embeddings API...")
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input="test"
    )
    print("✓ Embeddings API works!")
    
    print("\nTesting chat API...")
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Say 'test successful'"}],
        max_tokens=10
    )
    print(f"✓ Chat API works! Response: {response.choices[0].message.content}")
    
    print("\n✓ All tests passed! API key is valid.")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nPlease check your API key in .env file")
