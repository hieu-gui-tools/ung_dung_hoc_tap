import json
import re
from bs4 import BeautifulSoup

html = open('output.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

data = []

# Det thi trắc nghiệm often uses an iframe or script for quiz, or specific classes.
# Let's search all div elements to find where "Câu 1" is
for el in soup.find_all(text=re.compile("Câu 1")):
    parent = el.parent
    while parent and parent.name != 'body':
        if parent.has_attr('class'):
            data.append(f"Found Câu 1 in element with classes: {parent['class']}")
        parent = parent.parent

with open('structure.json', 'w', encoding='utf-8') as f:
    json.dump(data[:20], f, ensure_ascii=False, indent=2)
