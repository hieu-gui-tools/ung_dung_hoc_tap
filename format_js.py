js = open('script.js', encoding='utf-8').read()
lines = js.replace('{', '{\n').replace(';', ';\n').split('\n')
for line in lines:
    if 'ajax' in line or 'url:' in line or 'action' in line:
        print(line.strip()[:200])
