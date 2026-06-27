import re

js = open('script.js', encoding='utf-8').read()

m = re.search(r'\.iaeb-getresult.*?(click|href).*?\}', js, re.DOTALL)
if m:
    print(js[m.start():m.end()+100])
else:
    print("No click handler found.")
