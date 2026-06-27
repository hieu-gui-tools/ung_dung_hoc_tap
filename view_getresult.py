from bs4 import BeautifulSoup

html = open('output.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
el = soup.find(class_='iaeb-getresult')
with open('getresult.html', 'w', encoding='utf-8') as f:
    f.write(el.prettify() if el else 'none')
