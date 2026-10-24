"""Recheck two observed anomalies without printing customer contact data."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/sources'
rows = json.loads((DATA / 'workiz/lakewood_air/jobs.json').read_text())['data']
i = next(i for i, row in enumerate(rows) if row['UUID'] == 'J8OMKP')
job = rows[i]
assert job['Status'] == 'Done'
assert job['JobDateTime'] == '2026-11-10 10:00:00'
assert job['JobEndDateTime'] == '2026-11-10 12:00:00'
assert job['CreatedDate'] == '2025-11-01 10:00:00'
assert job['LastStatusUpdate'] == '2025-11-11 14:00:00'
assert rows[i - 1]['SerialId'] == 266 and rows[i + 1]['SerialId'] == 268
assert rows[i - 1]['JobDateTime'].startswith('2025-11-07')
assert rows[i + 1]['JobDateTime'].startswith('2025-11-10')
print('PASS: Workiz J8OMKP has conflicting years; neighboring records support a 2025 candidate correction.')

with (DATA / 'spreadsheet/rays_fixit_job_log.csv').open(newline='') as stream:
    sheet = list(csv.reader(stream))
original, duplicate, suspect = sheet[87], sheet[88], sheet[174]
phone = lambda value: re.sub(r'\D', '', value)[-10:]
assert original == duplicate
assert original[4] == '5823 Belmont Ave'
assert suspect[4] == '5832 belmont ave'
assert original[2] == suspect[2]
assert phone(original[3]) == phone(suspect[3])
assert suspect[0] == '08/14/2026' and suspect[5] == 'TV mount'
for name in ['fresh_nest_cleaning', 'greenville_ave_plumbing']:
    clients = json.loads((DATA / f'jobber/{name}.json').read_text())['data']['clients']['nodes']
    matches = [c for c in clients if any(phone(p['number']) == phone(suspect[3]) for p in c['phones'])]
    assert any(a['address']['street1'].lower() == '5823 belmont ave'
               for c in matches for a in c['properties']['nodes'])
print('PASS: CSV row 175 has a transposed-number candidate corroborated by earlier CSV rows and two Jobber accounts.')
print('These checks verify conflicting source evidence, not hidden ground truth or automatic repair correctness.')
