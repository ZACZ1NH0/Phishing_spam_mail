import requests

url = 'http://127.0.0.1:5000/predict'
files = {'file': open('./email/email2.eml', 'rb')}  # file .eml bạn muốn test

response = requests.post(url, files=files)

print(response.status_code)
print(response.json())  # In ra subject, body, prediction, saved_path
