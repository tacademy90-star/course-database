import os
import json
import re
import requests

# ── Config ──────────────────────────────────────────────
TOKEN  = os.environ['AIRTABLE_TOKEN']
TABLE  = 'tbl5BIWKSzPXBnd16'
BASES  = [
    'appjlWfyICYLj7kpS',   # APU / UNITAR / UTAR / MAHSA
    'appi7r3rUtJJ0MYa2',   # Lincoln / City / MMU / MSU / UNITEN / ALFA / UGM / UNIKL / AMU / SEGI
    'app0OjcAI4FMeq4Fc',   # UniCAM / UCSI / UNIRAZAK / second base
]
HEADERS = {'Authorization': f'Bearer {TOKEN}'}
# ────────────────────────────────────────────────────────


def slugify(name: str) -> str:
    """Turn a university name into a safe filename slug."""
    s = re.sub(r'[^\w\s-]', '', name.lower())
    s = re.sub(r'[\s_]+', '-', s)
    return re.sub(r'-+', '-', s).strip('-')


def clean(value) -> str:
    """Normalise any Airtable field value to a plain string."""
    if value is None:
        return ''
    if isinstance(value, list):
        return '\n'.join(str(i) for i in value)
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()


def fetch_all(base_id: str) -> list:
    """Fetch every record from the Courses table in one base."""
    url     = f'https://api.airtable.com/v0/{base_id}/{TABLE}'
    records = []
    offset  = None

    while True:
        params = {
            'pageSize': 100,
            'cellFormat': 'string',
            'timeZone': 'Asia/Kuala_Lumpur',
            'userLocale': 'en-us',
        }
        if offset:
            params['offset'] = offset

        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        records += data.get('records', [])
        offset   = data.get('offset')
        if not offset:
            break

    return records


def normalize(record: dict) -> dict:
    """Map an Airtable record to the standard JSON schema."""
    f = record.get('fields', {})
    return {
        'course_id':            clean(f.get('Course ID')),
        'university':           clean(f.get('University')),
        'faculty':              clean(f.get('Faculty')),
        'course_name':          clean(f.get('Course Name')),
        'level':                clean(f.get('Level')),
        'study_mode':           clean(f.get('Study Mode')),
        'course_duration':      clean(f.get('Course Duration')),
        'tuition_fee':          clean(f.get('Tuition Fee')),
        'yearly_fee_structure': clean(f.get('Yearly Fee Structure')),
        'total_fee':            clean(f.get('Total Fee')),
        'other_fees_package':   clean(f.get('Other Fees Package')),
        'intake_dates':         clean(f.get('Intake Dates')),
        'notes':                clean(f.get('Notes')),
    }


def main():
    by_uni: dict[str, list] = {}

    # 1. Collect all records from all bases
    for base_id in BASES:
        print(f'Fetching base {base_id} ...')
        raw = fetch_all(base_id)
        print(f'  → {len(raw)} records')

        for rec in raw:
            item = normalize(rec)
            uni  = item['university']
            if not uni or not item['course_name']:
                continue
            by_uni.setdefault(uni, []).append(item)

    total = sum(len(v) for v in by_uni.values())
    print(f'\nTotal: {total} courses across {len(by_uni)} universities\n')

    # 2. Write one JSON file per university
    filenames = []
    for uni, courses in sorted(by_uni.items()):
        filename = slugify(uni) + '.json'
        with open(filename, 'w', encoding='utf-8') as fh:
            json.dump(courses, fh, ensure_ascii=False, indent=2)
        filenames.append(filename)
        print(f'  {filename}  ({len(courses)} courses)')

    # 3. Regenerate index.json
    with open('index.json', 'w', encoding='utf-8') as fh:
        json.dump(sorted(filenames), fh, ensure_ascii=False, indent=2)

    print(f'\nindex.json updated — {len(filenames)} university files listed.')


if __name__ == '__main__':
    main()
