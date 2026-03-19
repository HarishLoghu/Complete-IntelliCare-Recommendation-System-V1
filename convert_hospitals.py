import csv
import json
import ast

rows = []
try:
    with open('backend/hospitals_data.csv', encoding='utf8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                depts_str = r.get('departments', '[]')
                depts = ast.literal_eval(depts_str)
                if not isinstance(depts, list):
                    depts = [x.strip() for x in str(depts_str).split(',')]
            except Exception:
                depts = [x.strip().strip("'") for x in r.get('departments', '').strip('[]').split(',')]
            
            clean_depts = [d.strip() for d in depts if d.strip()]
            rows.append({
                'name': r['name'],
                'lat': float(r['lat']),
                'lon': float(r['lon']),
                'departments': clean_depts
            })

    with open('frontend/src/hospitalsData.js', 'w', encoding='utf8') as f:
        f.write('export const HOSPITALS = ' + json.dumps(rows, indent=2) + ';\n')
    print('SUCCESS')
except Exception as e:
    print('ERROR:', e)
