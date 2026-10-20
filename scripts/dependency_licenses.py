"""Record actual installed dependency licenses and retain packaged notices."""
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
rows = []
for dist in sorted(metadata.distributions(), key=lambda x: x.metadata['Name'].lower()):
    name = dist.metadata['Name']
    if name.lower() == 'myatri':
        continue
    row = {'name': name, 'version': dist.version,
           'license_expression': dist.metadata.get('License-Expression'),
           'license_metadata': dist.metadata.get('License'), 'notices': []}
    for relative in dist.files or []:
        text = relative.as_posix()
        if '.dist-info/' not in text:
            continue
        tail = text.split('.dist-info/', 1)[1]
        if 'license' not in tail.lower() and not any(x in Path(tail).name.upper() for x in ('COPYING', 'NOTICE', 'AUTHORS')):
            continue
        source = Path(dist.locate_file(relative))
        if source.is_file():
            target = root / 'LICENSES/dependencies' / name / tail
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            row['notices'].append(target.relative_to(root).as_posix())
    rows.append(row)
(root / 'reports/dependency_licenses.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'packages': len(rows), 'notices': sum(len(r['notices']) for r in rows)}))
