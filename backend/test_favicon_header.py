import requests

try:
    response = requests.get("http://127.0.0.1:8000/favicon.svg")
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    if response.status_code == 200 and "image/svg+xml" in response.headers.get("Content-Type", ""):
        print("✅ Favicon served correctly with SVG MIME type!")
    else:
        print("❌ Failed to serve favicon correctly.")
except Exception as e:
    print(f"Error: {e}")
