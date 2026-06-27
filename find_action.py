import re

html = open('output.html', encoding='utf-8').read()
actions = re.findall(r'action\s*:\s*[\'\"]([a-zA-Z0-9_]+)[\'\"]', html)
print("Actions found:", set(actions))

# Also search for 'iaeb' in all js links to find the file that handles answers
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
for script in soup.find_all('script', src=True):
    if 'iaeb' in script['src'] or 'exam' in script['src']:
        print("JS file:", script['src'])
