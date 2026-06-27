import re

js = open('script.js', encoding='utf-8').read()
matches = re.findall(r'.{0,50}iaeb-correct.{0,50}', js)
for m in matches:
    print(m)
