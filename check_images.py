import requests
from bs4 import BeautifulSoup
import re

# Fetch one page to inspect images
url = "https://dethitracnghiem.vn/bai-thi/de-thi-bo-luat-moi-lai-xe-oto-hang-b-de-1/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

items = soup.find_all('div', class_='iaeb-item')
print(f"Total questions: {len(items)}")

with_img = 0
for item in items:
    q_div = item.find('div', class_='iaeb-quiz')
    if not q_div: continue
    
    img_tag = item.find('img')
    if img_tag:
        with_img += 1
        print("Image tag:", img_tag)

print(f"Questions with image: {with_img}")
