import re

html = open('output.html', encoding='utf-8').read()
for script in re.findall(r'<script.*?>.*?</script>', html, re.DOTALL):
    if 'FB_GATE' in script:
        print(script[:1000])
