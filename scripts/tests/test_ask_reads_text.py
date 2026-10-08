#!/usr/bin/env python3
"""Checks that the translation is read from the text blocks of the reply.

Claude Sonnet 5.5 thinks before answering, and the reply opens with a thinking
block. Reading the first block, as the script did for Sonnet 4.5, fails on it.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translate_diff import ask


class FakeMessages:
    def create(self, **kwargs):
        return SimpleNamespace(content=[
            SimpleNamespace(type='thinking', thinking=''),
            SimpleNamespace(type='text', text='Перший рядок\n'),
            SimpleNamespace(type='text', text='Другий рядок'),
        ])


def main() -> int:
    client = SimpleNamespace(messages=FakeMessages())
    reply = ask(client, 'system', 'glossary', 'prompt')

    if reply != 'Перший рядок\nДругий рядок':
        print(f'  unexpected reply: {reply!r}', file=sys.stderr)
        return 1

    print('ask reads text blocks: ok')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
