import requests
from bs4 import BeautifulSoup

url = "https://vndoc.com/tieng-anh-b1"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    soup = BeautifulSoup(r.text, 'html.parser')
    with open('vndoc_b1.txt', 'w', encoding='utf-8') as f:
        for a in soup.find_all('a', href=True):
            if 'b1' in a['href'].lower():
                f.write(f"{a.text.strip()} -> {a['href']}\n")
