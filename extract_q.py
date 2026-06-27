from bs4 import BeautifulSoup

html = open('output.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

items = soup.find_all('div', class_='iaeb-item')
if items:
    with open('question.html', 'w', encoding='utf-8') as f:
        f.write(items[0].prettify())
        if len(items) > 1:
            f.write("\n\n<!-- SECOND QUESTION -->\n\n")
            f.write(items[1].prettify())
