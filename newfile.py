import os
import requests

username = os.getenv("API_USERNAME")
password = os.getenv("API_PASSWORD")

url = "https://your-api-endpoint"
response = requests.get(url, auth=(username, password))

if response.status_code == 200:
    print("Authentication successful!")
else:
    print(f"Authentication failed! Status Code: {response.status_code}")
