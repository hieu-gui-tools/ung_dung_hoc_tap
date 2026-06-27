import requests
from bs4 import BeautifulSoup

url = 'https://dethitracnghiem.vn/bang-lai-xe-o-to-hang-b/'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

links = []
for a in soup.find_all('a', href=True):
    if 'de-thi' in a['href'] or 'de-so' in a['href'] or 'bang-lai-xe-o-to-hang-b' in a['href']:
        links.append(a['href'])

print("Links found:")
for link in set(links):
    print(link)
