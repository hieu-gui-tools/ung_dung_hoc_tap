import requests
import re
from bs4 import BeautifulSoup

url = "https://dethitracnghiem.vn/tu-vung-co-the-nguoi-cac-bo-phan-co-the-nguoi-tieng-anh/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

items = soup.find_all('div', class_=re.compile(r'iaeb-item'))
print(f"Found {len(items)} questions with iaeb-item")
