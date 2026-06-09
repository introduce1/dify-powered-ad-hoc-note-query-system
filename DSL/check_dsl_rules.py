import yaml
d = yaml.safe_load(open(r'c:\Users\17375\Desktop\现阶段工程文件\DSL\随记随查_宽松版.yml', encoding='utf-8'))
for n in d['workflow']['graph']['nodes']:
    if n['data']['type'] == 'if-else':
        for c in n['data'].get('cases', []):
            if c.get('id') == '773289b8-22d2-43c8-a8b5-f2d0aa95db92':
                print(f"Found node: {n['data']['title']}")
                for cond in c.get('conditions', []):
                    print(f"  - {cond['variable_selector']} {cond['comparison_operator']} {cond['value']}")
