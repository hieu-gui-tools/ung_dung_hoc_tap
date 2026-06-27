import requests
from bs4 import BeautifulSoup

url = 'https://dethitracnghiem.vn/bai-thi/de-thi-bo-luat-moi-lai-xe-oto-hang-b-de-1/'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

with open('output.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())
