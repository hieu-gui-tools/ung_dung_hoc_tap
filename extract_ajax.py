import re

js = open('script.js', encoding='utf-8').read()

ajax_calls = []
# Find lines with ajax, post, get
for i, line in enumerate(js.split('\n')):
    if 'ajax' in line.lower() or 'post' in line.lower() or 'fetch' in line.lower():
        ajax_calls.append(line)

with open('ajax.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(ajax_calls[:50]))
