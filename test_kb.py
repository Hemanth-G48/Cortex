import urllib.request
import json

try:
    req = urllib.request.urlopen("http://127.0.0.1:5173/knowledge-base")
    print("Status:", req.getcode())
    print("HTML snippet:", req.read().decode('utf-8')[:500])
except Exception as e:
    print("Error:", e)
