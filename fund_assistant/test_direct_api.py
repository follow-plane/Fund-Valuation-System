
import requests
import time
import re
import json

def test_direct_api():
    code = "110011"
    url = f"http://fundgz.1234567.com.cn/js/{code}.js"
    print(f"Fetching {url}...")
    
    start = time.time()
    try:
        resp = requests.get(url, timeout=2)
        print(f"Time: {time.time() - start:.4f}s")
        print(f"Status: {resp.status_code}")
        print(f"Text: {resp.text}")
        
        # Parse
        content = resp.text
        if "jsonpgz" in content:
            json_str = content[content.find('(')+1 : content.find(')')]
            data = json.loads(json_str)
            print("Parsed:", data)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_direct_api()
