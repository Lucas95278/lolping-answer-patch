"""Minimal answer settings and per-leaf, conditional restoration."""

import copy
import json

CHANGES = {
    ('teammate', 'intents', 'danger', 'enabled'): True,
    ('teammate', 'intents', 'danger', 'label'): 'MCQ',
    ('teammate', 'intents', 'danger', 'instruction'): 'Read the question and all available evidence. Return only the option letter(s). Do not show reasoning or pings.',
    ('teammate', 'intents', 'allin', 'enabled'): True,
    ('teammate', 'intents', 'allin', 'label'): 'FRQ',
    ('teammate', 'intents', 'allin', 'instruction'): 'Read the complete available article, tables and images. Answer every subpart in English, then Chinese. Use clear everyday English at about IELTS Writing 5.5. Give only the final answer.',
    ('teammate', 'receiptSound'): False,
    ('teammate', 'emotes'): False,
}


def load_settings(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise ValueError('Launch lolPing and configure an AI profile first; settings.json is missing.') from exc
    if not isinstance(data, dict):
        raise ValueError('settings.json must contain a JSON object.')
    return data


def apply_settings(data):
    result, snapshot = copy.deepcopy(data), []
    for path, value in CHANGES.items():
        node = result
        created = []
        for index, part in enumerate(path[:-1]):
            if part not in node:
                node[part] = {}
                created.append(list(path[:index + 1]))
            if not isinstance(node[part], dict):
                raise ValueError('Invalid settings structure at ' + '.'.join(path))
            node = node[part]
        key = path[-1]
        snapshot.append({'path': list(path), 'present': key in node,
                         'original': node.get(key), 'installed': value, 'created_parents': created})
        node[key] = value
    return result, snapshot


def restore_settings(data, snapshot):
    result = copy.deepcopy(data)
    for item in snapshot:
        node = result
        parents = []
        for part in item['path'][:-1]:
            if not isinstance(node, dict) or not isinstance(node.get(part), dict):
                break
            parents.append((node, part))
            node = node[part]
        else:
            key = item['path'][-1]
            if key in node and type(node[key]) is type(item['installed']) and node[key] == item['installed']:
                if item['present']:
                    node[key] = item['original']
                else:
                    del node[key]
    created = {tuple(path) for item in snapshot for path in item.get('created_parents', [])}
    for path in sorted(created, key=len, reverse=True):
        node = result
        for part in path[:-1]:
            if not isinstance(node, dict) or not isinstance(node.get(part), dict):
                break
            node = node[part]
        else:
            if isinstance(node, dict) and node.get(path[-1]) == {}:
                del node[path[-1]]
    return result
