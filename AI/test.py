import requests

API_KEY = "AIzaSyD6UKiGqfVi1Qi7LpPYMH9_ap2Gm22fPJI" 

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

response = requests.get(url)

print("Status:", response.status_code)
print(response.text)