"""Report source shapes and counts without copying customer records."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def read_json(path):
    return json.loads(path.read_text())


def inspect():
    files = sorted(p for p in DATA.rglob('*') if p.is_file())
    report = {'files': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
                         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    counts = Counter(files=len(files), bytes=sum(p.stat().st_size for p in files))
    statuses = {}
    for path in sorted((DATA / 'sources/jobber').glob('*.json')):
        data = read_json(path)['data']
        counts['jobber_accounts'] += 1
        counts['jobber_clients'] += len(data['clients']['nodes'])
        counts['jobber_properties'] += sum(len(c['properties']['nodes']) for c in data['clients']['nodes'])
        for job in data['jobs']['nodes']:
            counts['jobber_jobs'] += 1
            statuses.setdefault('jobber_jobs', Counter())[job['jobStatus']] += 1
            for visit in job['visits']['nodes']:
                counts['jobber_visits'] += 1
                statuses.setdefault('jobber_visits', Counter())[visit['visitStatus']] += 1
    duplicates = []
    for company in sorted((DATA / 'sources/housecall_pro').iterdir()):
        if not company.is_dir():
            continue
        counts['hcp_accounts'] += 1
        for kind in ['customers', 'jobs', 'estimates']:
            rows = []
            pages = sorted(company.glob(f'{kind}_page_*.json'))
            for page in pages:
                data = read_json(page)
                assert len(pages) == data['total_pages'], page
                rows.extend(data[kind])
                if kind != 'customers':
                    statuses.setdefault(f'hcp_{kind}', Counter()).update(r['work_status'] for r in data[kind])
            counts[f'hcp_{kind}'] += len(rows)
            counts[f'hcp_{kind}_unique_source_ids'] += len({r['id'] for r in rows})
            ids = Counter(r['id'] for r in rows)
            for source_id, n in ids.items():
                if n > 1:
                    copies = [r for r in rows if r['id'] == source_id]
                    duplicates.append({'account': company.name, 'kind': kind, 'source_id': source_id,
                                       'occurrences': n, 'identical_payloads': len({json.dumps(r, sort_keys=True) for r in copies}) == 1})
    for path in sorted((DATA / 'sources/workiz').glob('*/jobs.json')):
        data = read_json(path)
        assert data['found'] == len(data['data']) and not data['has_more'], path
        counts['workiz_accounts'] += 1
        counts['workiz_jobs'] += len(data['data'])
        statuses.setdefault('workiz_jobs', Counter()).update(r['Status'] for r in data['data'])
    with (DATA / 'sources/spreadsheet/rays_fixit_job_log.csv').open(newline='') as stream:
        rows = list(csv.reader(stream))
    assert rows[2] == ['Date', 'Time', 'Customer', 'Phone', 'Address', 'Job', '$', 'Paid?', 'Notes']
    counts['csv_data_rows'] = len(rows) - 3
    counts['csv_exact_duplicate_rows'] = len(rows[3:]) - len(set(map(tuple, rows[3:])))
    profiles = read_json(DATA / 'sources/profiles/providers.json')['providers']
    counts['provider_profiles'] = len(profiles)
    report['profile_hours_shapes'] = dict(Counter(type(p['hours']).__name__ for p in profiles))
    calendars = {}
    for path in sorted((DATA / 'sources/calendars').glob('*.ics')):
        text = path.read_text().replace('\n ', '').replace('\n\t', '')
        events = [part.split('END:VEVENT', 1)[0] for part in text.split('BEGIN:VEVENT')[1:]]
        props = Counter(line.split(':', 1)[0].split(';', 1)[0] for event in events for line in event.splitlines() if ':' in line)
        calendars[path.name] = {'events': len(events), 'event_property_counts': dict(props)}
        counts['calendar_events'] += len(events)
    with (DATA / 'reference/street_segments.csv').open(newline='') as stream:
        segments = list(csv.DictReader(stream))
    counts['street_segments'] = len(segments)
    report.update(counts=dict(counts), statuses=statuses, repeated_source_ids=duplicates, calendars=calendars,
                  reference_postal_codes=sorted({r['zip'] for r in segments}))
    return report


if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2, sort_keys=True))
