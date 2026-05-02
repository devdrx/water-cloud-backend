import json
import re

path = r'c:\Users\devda\OneDrive\Desktop\water-cloud-backend\grafana\provisioning\dashboards\water_quality.json'

with open(path, 'rb') as f:
    raw = f.read()

# Try to decode as utf-8, but be safe
try:
    data = raw.decode('utf-8')
except UnicodeDecodeError:
    data = raw.decode('latin-1')

# Fix corrupted sequences that often appear in these logs
# Note: These are literal strings seen in previous turns
corrections = {
    'ðŸ“Š': '📊',
    'ðŸ“ˆ': '📈',
    'ðŸ”¬': '🔬',
    'ðŸ“‹': '📋',
    'âœ…': '✅',
    'ðŸŸ¢': '🟢',
    'ðŸŸ¡': '🟡',
    'ðŸŸ ': '🟠',
    'ðŸ”´': '🔴',
    'âš ï¸ ': '⚠️',
    'AS/cm': 'μS/cm',
    'o. Yes': '✅ Yes',
    '?O No': '❌ No',
    's,?': '⚠️'
}

for old, new in corrections.items():
    data = data.replace(old, new)

# Ensure no other mangled emoji remnants
data = re.sub(r'ðŸ[^\s\"]+', '🔹', data) 

try:
    obj = json.loads(data)
except json.JSONDecodeError as e:
    # If it fails, we might have over-replaced. Fallback to basic load.
    print(f"JSON Error: {e}")
    # We will try to just fix the DS_uid part and encoding
    data = raw.decode('utf-8', errors='ignore')
    data = data.replace('${DS_WATERQUALITYDB}', 'DS_WATERQUALITYDB')
    obj = json.loads(data)

# Force all datasource blocks to be consistent
def fix_ds(d):
    if isinstance(d, dict):
        if 'datasource' in d and isinstance(d['datasource'], dict):
            ds = d['datasource']
            if ds.get('type') == 'postgres' or ds.get('uid') == 'DS_WATERQUALITYDB':
                ds['type'] = 'postgres'
                ds['uid'] = 'DS_WATERQUALITYDB'
        for v in d.values():
            fix_ds(v)
    elif isinstance(d, list):
        for item in d:
            fix_ds(item)

fix_ds(obj)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(obj, f, indent=2, ensure_ascii=False)

print("Dashboard cleanup COMPLETE")
