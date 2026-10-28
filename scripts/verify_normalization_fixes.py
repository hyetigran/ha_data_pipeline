"""Verify before/after normalization snapshots and summarize six MCP answers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


def metrics(db):
    counts = {table:db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
              for table in ('source_records','occurrences','canonical_providers',
                            'canonical_jobs','canonical_visits','canonical_properties')}
    counts['only_unknown_jobs'] = db.execute("SELECT count(*) FROM (SELECT job_id FROM job_services GROUP BY job_id HAVING sum(service_code!='unknown')=0)").fetchone()[0]
    counts['only_unknown_completed_jobs'] = db.execute("SELECT count(*) FROM (SELECT j.job_id FROM job_services j WHERE EXISTS(SELECT 1 FROM service_completions c WHERE c.job_id=j.job_id) GROUP BY j.job_id HAVING sum(service_code!='unknown')=0)").fetchone()[0]
    counts['review'] = dict(Counter(json.loads(r[0])['kind'] for r in db.execute('SELECT document FROM reconciliation_proposals')))
    return counts


def service_rows(db):
    result = defaultdict(set)
    for job,trade,service in db.execute('SELECT job_id,trade_code,service_code FROM job_services'):
        result[job].add((trade,service))
    return result


def summarize(answers):
    q={key:value['answer']['results'] for key,value in answers.items()}
    groups=Counter()
    for g in q['Q1']['groups']['items']:
        groups[g['trade']]+=g['distinct_jobs']
    return {
        'Q1':dict(sorted(groups.items())),
        'Q2':[{'provider':p['business_name'],'relevant_jobs':p['completed_relevant_jobs'],
               'openings':p['availability']['openings']['items']} for p in q['Q2']['providers']['items']],
        'Q3':[{'provider':v['business_name'],'services':v['services']['items'],
               'start':v['start_utc'],'end':v['end_utc']} for v in q['Q3']['visits']['items']],
        'Q4':{'completed_jobs':q['Q4']['completed_distinct_jobs'],'trades':q['Q4']['trades']['items'],
               'declared_zips':q['Q4']['declared_service_postal_codes']['items'],
               'openings':q['Q4']['availability']['openings']['items']},
        'Q5':{'completed_jobs':q['Q5']['distinct_jobs'],
               'jobs':[{'provider':j['business_name'],'services':j['services']['items'],
                        'completion_dates':[c['service_date'] for c in j['completions']['items']]}
                       for j in q['Q5']['jobs']['items']]},
        'Q6':{'eligible':q['Q6']['providers']['total'],
               'durations':{p['business_name']:p['duration'] for p in q['Q6']['excluded']['items'] if p.get('duration')}},
    }


def verify(root: Path):
    before=sqlite3.connect((root/'before.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    after=sqlite3.connect((root/'after.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    try:
        b,a=metrics(before),metrics(after)
        for key in ('source_records','occurrences','canonical_providers','canonical_jobs','canonical_visits'):
            assert b[key]==a[key],key
        for kind in ('provider','job','visit'):
            sql='SELECT source_id,canonical_id FROM canonical_crosswalk WHERE kind=? ORDER BY source_id'
            assert before.execute(sql,(kind,)).fetchall()==after.execute(sql,(kind,)).fetchall()
        assert after.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not after.execute('PRAGMA foreign_key_check').fetchall()
        assert after.execute('SELECT count(*) FROM field_lineage WHERE decision_id IS NOT NULL').fetchone()[0]==0
        assert a['review']['provider_match']==3 and a['review']['field_correction']==3
        proposals=[json.loads(r[0]) for r in after.execute('SELECT document FROM reconciliation_proposals')]
        assert all(p['human']['decision']=='defer' for p in proposals)
        old_services,new_services=service_rows(before),service_rows(after)
        expected={
            'gutter clean out':('gutters','gutters'),'gutter cleaning':('gutters','gutters'),
            'gutters cleaned':('gutters','gutters'),'leak in roof':('roofing','roofing'),
            'washer not draining':('appliance_repair','appliance_repair'),
            'heating repair':('hvac','hvac'),'wh replace':('plumbing','water_heater'),
            'assemble ikea':('handyman','furniture_assembly'),
        }
        checked=Counter()
        trailing=Counter()
        for job,raw in after.execute("SELECT x.canonical_id,r.raw_json FROM source_records r JOIN canonical_crosswalk x ON x.source_id=r.id AND x.kind='job' WHERE r.kind='job'"):
            row=json.loads(raw)
            label=str(row.get('title',row.get('description',row.get('JobType',row.get('Job',''))))).lower()
            if label in expected:
                assert new_services[job]=={expected[label]},label
                checked[label]+=1
            if row.get('Job') and row.get('Address','').lower().endswith(' dallas'):
                prop=after.execute('SELECT p.geocode_precision,p.unit FROM canonical_jobs j JOIN canonical_properties p ON p.id=j.property_id WHERE j.id=?',(job,)).fetchone()
                trailing[prop[0]]+=1
                if ', b dallas' in row['Address'].lower():
                    assert prop[1]=='b'
        assert sum(checked[k] for k in ('gutter clean out','gutter cleaning','gutters cleaned'))==134
        assert trailing=={'street_segment_interpolation':22,'missing':2}
        year=after.execute("SELECT v.scheduled_start_state FROM source_records r JOIN canonical_crosswalk x ON x.source_id=r.id AND x.kind='job' JOIN canonical_visits v ON v.job_id=x.canonical_id WHERE r.source_key='J8OMKP'").fetchall()
        assert year and all(r[0]=='disputed' for r in year)
        transposed=after.execute("SELECT p.house_number FROM source_records r JOIN canonical_crosswalk x ON x.source_id=r.id AND x.kind='job' JOIN canonical_jobs j ON j.id=x.canonical_id JOIN canonical_properties p ON p.id=j.property_id WHERE lower(json_extract(r.raw_json,'$.Address'))='5832 belmont ave'").fetchall()
        assert transposed==[(5832,)]
        for file,digest in json.loads((root/'input-hashes.json').read_text()).items():
            assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==digest,file
        old=json.loads((root/'before/answers.json').read_text())
        new=json.loads((root/'after-corrected/answers.json').read_text())
        old_history={j['job_id']:j for j in old['Q4']['answer']['results']['history']['items']}
        changed_history=sum(j['services']!=old_history[j['job_id']]['services']
            for j in new['Q4']['answer']['results']['history']['items'])
        return {'status':'pass','metrics':{'before':b,'after':a},
                'jobs_with_changed_service_scope':sum(old_services[k]!=new_services[k] for k in old_services),
                'verified_raw_label_counts':dict(checked),'trailing_city_address_precision':dict(trailing),
                'lone_star_changed_services_in_first_100_jobs':changed_history,
                'source_and_review_files_unchanged':True,'all_review_proposals_deferred':True,
                'answers':{'before':summarize(old),'after':summarize(new)}}
    finally:
        before.close()
        after.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.evidence)
    (args.evidence/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'comparison':str(args.evidence/'comparison.json')}))
