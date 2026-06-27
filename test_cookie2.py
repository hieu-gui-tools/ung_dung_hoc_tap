import requests
import json
import urllib.parse
from bs4 import BeautifulSoup

url = 'https://dethitracnghiem.vn/bai-thi/de-thi-bo-luat-moi-lai-xe-oto-hang-b-de-1/'
post_id = '90022'

dummy_answers = ["A"] * 35
cookie_obj = {f"exam_{post_id}": dummy_answers}

cookies = {
    'iaeb_answered': urllib.parse.quote(json.dumps(cookie_obj)),
    'iatup_post': urllib.parse.quote(json.dumps(f"post_{post_id}")),
    'iatup_ip': '1.1.1.1'
}

response = requests.get(url, cookies=cookies)
soup = BeautifulSoup(response.text, 'html.parser')

items = soup.find_all('div', class_='iaeb-item')
if not items:
    print("No items.")
else:
    q1 = items[0]
    print("q1 classes:", q1.get('class'))
    for li in q1.find_all('li'):
        print(f"li data-answer={li.get('data-answer')} classes={li.get('class')}")
    sol = q1.find('div', class_='iaeb-solution-content')
    if sol:
        print("Solution:", sol.text.strip())
