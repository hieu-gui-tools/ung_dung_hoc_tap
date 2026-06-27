import re

js = open('script.js', encoding='utf-8').read()
m = re.search(r'function iaeb_handle_exam_end.*?catch\(error\)\{.*?\}', js, re.DOTALL)
if m:
    with open('func.txt', 'w', encoding='utf-8') as f:
        f.write(js[m.start():m.end()+150])
