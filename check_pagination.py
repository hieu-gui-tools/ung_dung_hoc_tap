import requests
from bs4 import BeautifulSoup

url = "https://dethitracnghiem.vn/kien-thuc/tieng-anh/tu-vung/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

pagination = soup.find('div', class_='nav-links') or soup.find(class_='pagination')
if pagination:
    print("Found pagination!")
    for a in pagination.find_all('a'):
        print(f"Page link: {a['href']}")
else:
    print("No pagination found on tu-vung.")
