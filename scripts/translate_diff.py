#!/usr/bin/env python3
"""Bring translated pages up to date with an upstream diff.

Only the sections the diff touches are sent to the model, never whole files.
Documentation pages run to four thousand lines while a typical upstream commit
changes twenty, and output tokens cost five times what input does - sending
`strings.md` back in full to retitle one method would cost more than the entire
rest of the run. Untouched sections are copied through byte for byte, so the
model cannot damage what it never saw.

The result is checked by validate_translation.py before it is written.
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

from validate_translation import problems

# Imported inside main(): the section-splitting logic below is the part worth
# testing, and it should not need the SDK installed to run.

MODEL = 'claude-sonnet-4-5'

# Sections start at an anchor; everything before the first one is the preamble
# (header, title, contents list) and travels as its own unit.
SECTION = re.compile(r'(?=^<a\s+name="[^"]+"></a>$)', re.MULTILINE)

# Inline base64 payloads: mcp.md carries a 35KB image on one line.
EMBEDDED = re.compile(r'data:[a-z]+/[a-z.+-]+;base64,')

SYSTEM = """\
Ти перекладаєш документацію Laravel англійською на українську для
laravelukraine.com.

Тобі дають фрагмент чинного українського перекладу і diff відповідного
фрагмента англійського оригіналу. Твоє завдання - оновити український текст
так, щоб він відповідав новому англійському, змінивши рівно те, що змінилось.

Правила:
- Не чіпай нічого, крім того, що змінює diff. Решту речень повертай дослівно.
- Зберігай розмітку точно: кількість рядків, порожні рядки, відступи,
  блоки коду, атрибути на кшталт {.collection-method}.
- Не перекладай код, назви класів, методів, змінних, ключі конфігурації.
- Якорі <a name="..."></a> лишаються англійською незмінними.
- Посилання виду /docs/{{version}}/... не змінюй.
- Дотримуйся глосарія, наведеного нижче.
- Тире - звичайний дефіс, не довге тире.

- Кількість рядків має точно збігатися з оригіналом фрагмента, включно з
  порожніми рядками на початку та в кінці.

Повертай ТІЛЬКИ оновлений український текст фрагмента, без пояснень і без
огорнення у блок коду.\
"""

# A section upstream added outright has no Ukrainian counterpart to update, so
# the diff-based prompt above has nothing to anchor on. It is translated whole
# instead, under the same structural rules.
SYSTEM_NEW = """\
Ти перекладаєш документацію Laravel англійською на українську для
laravelukraine.com.

Тобі дають новий фрагмент англійської документації, якого ще немає в
українському перекладі. Переклади його повністю.

Правила:
- Зберігай розмітку точно: кількість рядків, порожні рядки, відступи,
  блоки коду, атрибути на кшталт {.collection-method}.
- Не перекладай код, назви класів, методів, змінних, ключі конфігурації.
- Якорі <a name="..."></a> лишаються англійською незмінними.
- Посилання виду /docs/{{version}}/... не змінюй.
- Заголовки на кшталт #### array_keys:_foo_,_bar_,... - це імена правил, а не
  проза: лишай їх незмінними.
- Дотримуйся глосарія, наведеного нижче.
- Тире - звичайний дефіс, не довге тире.

- Кількість рядків має точно збігатися з англійським фрагментом, включно з
  порожніми рядками на початку та в кінці.

Повертай ТІЛЬКИ український переклад фрагмента, без пояснень і без огорнення
у блок коду.\
"""


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True,
                          check=True).stdout


def split_sections(text: str) -> list[str]:
    return SECTION.split(text)


def anchor_of(section: str) -> str | None:
    match = re.match(r'^<a\s+name="([^"]+)"></a>', section)

    return match.group(1) if match else None


def changed_anchors(base: str, head: str, path: str) -> set[str]:
    """Which sections of a file the diff touches.

    Hunk headers carry the enclosing context, but not reliably enough to trust,
    so line numbers are mapped onto the section boundaries of the new file.
    """
    new_text = git('show', f'{head}:{path}')
    sections = split_sections(new_text)

    # Line number where each section starts, 1-based.
    bounds: list[tuple[int, int, str | None]] = []
    line = 1

    for section in sections:
        length = len(section.splitlines())
        bounds.append((line, line + length - 1, anchor_of(section)))
        line += length

    touched: set[str] = set()
    diff = git('diff', '-U0', base, head, '--', path)

    for header in re.finditer(r'^@@ -\S+ \+(\d+)(?:,(\d+))? @@', diff, re.MULTILINE):
        start = int(header.group(1))
        count = int(header.group(2) or 1)
        end = start + max(count - 1, 0)

        for low, high, anchor in bounds:
            if start <= high and end >= low:
                # None marks the preamble, which has no anchor of its own.
                touched.add(anchor or '')

    return touched


def ask(client, system: str, glossary: str, prompt: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=[
            {'type': 'text', 'text': system},
            # Cached so a run that makes several calls pays for the glossary
            # once. Across runs the cache has expired, which is why nothing
            # else here is marked: writing a cache entry costs more than a
            # plain read when it is never read back.
            {'type': 'text', 'text': f'Глосарій:\n\n{glossary}',
             'cache_control': {'type': 'ephemeral'}},
        ],
        messages=[{'role': 'user', 'content': prompt}],
    )

    return message.content[0].text


def translate(client, glossary: str, current: str, diff: str) -> str:
    return ask(client, SYSTEM, glossary,
               f'Чинний український переклад фрагмента:\n\n{current}\n\n'
               f'Diff англійського оригіналу цього фрагмента:\n\n{diff}')


def translate_new(client, glossary: str, section: str) -> str:
    return ask(client, SYSTEM_NEW, glossary,
               f'Новий фрагмент англійського оригіналу:\n\n{section}')


def rebuild(current: str, upstream: str, touched: set[str],
            update, create) -> tuple[str, list[str], list[str]]:
    """Assemble the updated translation, in upstream's section order.

    `update(anchor, section)` refreshes a section we already have; `create`
    translates one upstream added. Either may return None to leave the section
    to a person. Returns the page plus the anchors added and deferred.

    Order comes from upstream so that a new section lands in the right place -
    and so that walking our own sections cannot silently skip it, which is the
    bug this function exists to make impossible.
    """
    mine = {anchor_of(section) or '': section
            for section in split_sections(current)}

    rebuilt: list[str] = []
    added: list[str] = []
    deferred: list[str] = []

    for upstream_section in split_sections(upstream):
        anchor = anchor_of(upstream_section) or ''
        section = mine.get(anchor)

        if section is None:
            translated = create(anchor, upstream_section)

            if translated is None:
                deferred.append(anchor or '(преамбула)')
                continue

            rebuilt.append(restore_edges(upstream_section, translated))
            added.append(anchor)
            continue

        if anchor not in touched:
            rebuilt.append(section)
            continue

        translated = update(anchor, section)

        if translated is None:
            rebuilt.append(section)
            deferred.append(anchor or '(преамбула)')
            continue

        rebuilt.append(restore_edges(section, translated))

    return ''.join(rebuilt), added, deferred


def restore_edges(original: str, translated: str) -> str:
    """Put back the blank lines that separate this section from the next.

    Sections end in blank lines, and a model reliably strips them: they carry
    no meaning to read, so returning "just the text" drops them. That silently
    shortens every translated section by two lines and fails the line-count
    check, which is how this was found. Rather than ask the prompt to be
    careful about invisible characters, the boundaries are reattached here.
    """
    body = translated.strip('\n')

    leading = len(original) - len(original.lstrip('\n'))
    trailing = len(original) - len(original.rstrip('\n'))

    return ('\n' * leading) + body + ('\n' * trailing)


def section_diff(base: str, head: str, path: str, anchor: str) -> str:
    """The diff limited to one section, for context in the prompt."""
    def find(commit: str) -> str:
        for section in split_sections(git('show', f'{commit}:{path}')):
            if (anchor_of(section) or '') == anchor:
                return section

        return ''

    before, after = find(base), find(head)

    if before == after:
        return ''

    return ''.join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile='before', tofile='after', n=3,
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('--base', required=True, help='commit we translated from')
    parser.add_argument('--head', required=True, help='commit to catch up to')
    args = parser.parse_args()

    if not os.environ.get('ANTHROPIC_API_KEY'):
        print('ANTHROPIC_API_KEY is not set', file=sys.stderr)
        return 1

    import anthropic

    # The header stores the full hash, and callers pass whatever git gave them
    # - an abbreviated one would be written straight through and quietly fail
    # the header check on the next run.
    base = git('rev-parse', args.base).strip()
    head = git('rev-parse', args.head).strip()

    client = anthropic.Anthropic()
    glossary = Path('GLOSSARY.md').read_text()
    failed = False

    for name in args.files:
        path = Path(name)

        if not path.exists():
            print(f'{name}: not translated yet - skipping', file=sys.stderr)
            continue

        touched = changed_anchors(base, head, name)

        if not touched:
            continue

        # Both paths refuse a section carrying an embedded data: URI - a single
        # line tens of thousands of characters long, almost none of it
        # translatable, which a model asked to echo back may silently truncate
        # or alter, replacing a working image with a corrupt one. Reported and
        # left for a person instead.
        def update(anchor: str, section: str) -> str | None:
            diff = section_diff(base, head, name, anchor)

            if not diff:
                return section

            if EMBEDDED.search(section):
                print(f'{name}: section "{anchor}" holds embedded data - left for a person',
                      file=sys.stderr)
                return None

            return translate(client, glossary, section, diff)

        def create(anchor: str, section: str) -> str | None:
            if EMBEDDED.search(section):
                print(f'{name}: new section "{anchor}" holds embedded data '
                      '- left for a person', file=sys.stderr)
                return None

            return translate_new(client, glossary, section)

        updated, added, deferred = rebuild(
            path.read_text(), git('show', f'{head}:{name}'), touched, update, create,
        )

        # The header records what the file is now in step with.
        updated = re.sub(r'^git: [0-9a-f]{40}$', f'git: {head}',
                         updated, count=1, flags=re.MULTILINE)

        # Checked before writing, against the upstream file it now claims to
        # match. A dropped anchor breaks the sidebar and every deep link into
        # the page, and reads as an ordinary wording change in review - the
        # kind of thing a person skims past, so it must not reach the branch.
        found = problems(git('show', f'{head}:{name}'), updated)

        if found:
            print(f'{name}: rejected', file=sys.stderr)

            for problem in found:
                print(f'  - {problem}', file=sys.stderr)

            failed = True
            continue

        path.write_text(updated)

        notes = []

        if added:
            notes.append(f'{len(added)} new')
        if deferred:
            notes.append(f'{len(deferred)} left for a person')

        note = f' ({", ".join(notes)})' if notes else ''
        print(f'{name}: {len(touched)} sections{note}')

    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
