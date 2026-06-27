import json
from bs4 import BeautifulSoup

html = open('output.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

items = soup.find_all('div', class_='iaeb-item')
if items:
    q1 = items[0]
    print("q1 attrs:", q1.attrs)
    for li in q1.find_all('li'):
        print("li attrs:", li.attrs)
    
    # Are there any other hidden elements?
    for el in q1.find_all(True):
        if 'data' in str(el.attrs):
            pass # we already checked li

    # Is there a global object?
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'iaeb' in script.string:
            print("--- script ---")
            print(script.string[:500])
