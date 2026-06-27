import requests
from bs4 import BeautifulSoup

url = "https://vi.englishteststore.net/vstep-b1-b2-c1/20-de-luyen-thi-tieng-anh-b1-kem-dap-an/"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
print(r.status_code)

if r.status_code == 200:
    soup = BeautifulSoup(r.text, 'html.parser')
    with open('vi_englishteststore_b1.txt', 'w', encoding='utf-8') as f:
        # Just extract text to see the structure
        main = soup.find('div', class_='item-page') or soup.find('body')
        for p in main.find_all(['p', 'h3', 'div']):
            text = p.text.strip()
            if text:
                f.write(text + "\n")
