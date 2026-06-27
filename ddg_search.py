import requests
from bs4 import BeautifulSoup

def search(query):
    url = "https://html.duckduckgo.com/html/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    data = {'q': query}
    r = requests.post(url, data=data, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    for a in soup.find_all('a', class_='result__url'):
        print(a.get('href'))

search('đề thi trắc nghiệm tiếng anh b1')
