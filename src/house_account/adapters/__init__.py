import json
from collections.abc import Iterator
from pathlib import Path

from house_account.model import Observation

from . import crm, other

ADAPTERS = {
    'jobber': crm._jobber,
    'housecall_pro': crm._housecall_pro,
    'workiz': crm._workiz,
    'spreadsheet': other._spreadsheet,
    'calendars': other._calendars,
    'profiles': other._profiles,
    'reference': other._reference,
}


def load(root: Path) -> Iterator[Observation]:
    for adapter in ADAPTERS.values():
        yield from adapter(root)

def file_role(name: str, path: Path) -> str:
    if name.endswith(('.DS_Store', 'README.md')):
        return 'metadata'
    if name.startswith('sources/housecall_pro/') and '_page_' in name:
        content = json.loads(path.read_text())
        collection = path.stem.split('_page_')[0]
        if collection in content and content[collection] == [] and content.get('total_items') == 0:
            return 'validated_empty_page'
    return 'source'
