#!/usr/bin/env python3
"""Report how far the translation has fallen behind laravel/docs.

Every translated page carries the upstream commit it was translated from in its
`git:` header, so the gap is derived from the files themselves - there is no
separate state file to keep in sync.

Prints a JSON report and decides which of two paths the change takes: small
enough to translate automatically, or large enough that it wants a person.
Writes the verdict to $GITHUB_OUTPUT when running under Actions.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HEADER = re.compile(r'^git:\s*([0-9a-f]{40})\s*$', re.MULTILINE)

# Ours, not upstream's: no `git:` header, and nothing to sync.
NOT_TRANSLATIONS = {'GLOSSARY.md', 'readme.md', 'license.md'}


def git(*args: str) -> str:
    return subprocess.run(
        ['git', *args], capture_output=True, text=True, check=True,
    ).stdout.strip()


def translated_at() -> tuple[str | None, dict[str, str]]:
    """The upstream commit each page was translated from, and the oldest one.

    The per-page headers are what the diff actually runs from - a page is
    behind by its own header and nothing else. The oldest is returned too, but
    only to report the span of the gap and to link the compare view; it is not
    a base to diff any particular file against.
    """
    per_file: dict[str, str] = {}

    for path in sorted(Path('.').glob('*.md')):
        if path.name in NOT_TRANSLATIONS:
            continue

        match = HEADER.search(path.read_text()[:400])

        if match:
            per_file[path.name] = match.group(1)

    if not per_file:
        return None, {}

    # Furthest behind, for the report. Distance is counted towards upstream, so
    # the one with the most commits still to come is the oldest.
    oldest = max(
        set(per_file.values()),
        key=lambda sha: int(git('rev-list', '--count', f'{sha}..upstream/13.x') or 0),
    )

    return oldest, per_file


def changed_since(per_file: dict[str, str], head: str) -> list[dict]:
    """What each page has to catch up on, measured from its own header.

    A single shared base - the oldest header across the whole translation - is
    wrong for any page not sitting on it, and wrong in the expensive direction:
    the page is diffed across commits it has already been brought through, so
    edits it already carries are offered for translation a second time.

    head.md is how this surfaced. It was translated by hand and its header was
    current, but the run diffed it from a commit predating the file's existence
    upstream, which reported all 762 of its lines as pending and filed it as
    "too large for automation" every morning. Measured from its own header it
    has nothing to do at all.

    The same arithmetic quietly inflated the rest: 1234 lines across 37 files
    from the shared base, against 73 lines across 7 files from the real ones.
    """
    changed: list[dict] = []

    for name, base in sorted(per_file.items()):
        if base == head:
            continue

        rows = git('diff', '--numstat', base, head, '--', name).splitlines()

        for row in rows:
            added, removed, _ = row.split('\t')

            # Binary files report '-'; upstream has none in *.md, but be safe.
            count = ((int(added) if added != '-' else 0)
                     + (int(removed) if removed != '-' else 0))

            if count:
                changed.append({'file': name, 'lines': count,
                                'base': base, 'known': True})

    return changed


def select(changed: list[dict], new_pages: list[str], max_file_lines: int,
           max_lines: int) -> tuple[list[dict], list[str], list[str]]:
    """Split the changed pages into what this run translates and what waits.

    Two limits, and they defer for different reasons - which is why the two
    lists come back separately rather than as one bag of "too big".

    The per-file limit is the real one: a page rewritten at length wants a
    person, and deferring it must not hold back the one-line fixes that came
    with it. Those are exactly what automation should be clearing.

    The run-wide limit is only a budget. It used to discard the whole run on
    overflow, which is how thirty-six pages of one and two line fixes came to
    be reported as "too large for automation" behind a single 762-line page:
    the budget was 400, the small pages added up to 472, and all of them were
    thrown away over the 72-line excess. Worse, it could not recover - nothing
    translated meant no `git:` header moved, so the next day's diff spanned the
    same commits and overflowed again.

    So the budget is filled instead of abandoned, smallest first: the run
    clears as many pages as it can afford, their headers move, and the pages
    left over are a smaller diff tomorrow rather than the same one.
    """
    oversized = [c['file'] for c in changed if c['lines'] > max_file_lines]
    eligible = [c for c in changed
                if c['lines'] <= max_file_lines and c['file'] not in new_pages]

    routine: list[dict] = []
    over_budget: list[str] = []
    spent = 0

    # Smallest first, so the budget buys the most pages. A page skipped for
    # want of budget is not skipped for want of room after it: once the budget
    # is spent, everything larger waits too, rather than letting a later small
    # page jump a queue it did not earn.
    for page in sorted(eligible, key=lambda c: c['lines']):
        if spent + page['lines'] > max_lines:
            over_budget.append(page['file'])
            continue

        routine.append(page)
        spent += page['lines']

    # Back into the order the diff reported, which is upstream's own: the file
    # list travels to git as arguments and reads better alphabetically than by
    # size.
    order = [c['file'] for c in changed]
    routine.sort(key=lambda c: order.index(c['file']))
    over_budget.sort(key=order.index)

    return routine, oversized, over_budget


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-lines', type=int, default=400,
                        help='total diff size above which the run is capped')
    parser.add_argument('--max-file-lines', type=int, default=150,
                        help='per-file size above which a page waits for a person')
    parser.add_argument('--upstream', default='upstream/13.x')
    args = parser.parse_args()

    base, per_file = translated_at()

    if base is None:
        print('No translated pages carry a git: header.', file=sys.stderr)
        return 1

    head = git('rev-parse', args.upstream)

    # Each page is measured from the commit it was itself translated from.
    changed = changed_since(per_file, head)

    # A file upstream has that we have never translated is a new page, not an
    # edit - it needs a title, a slug and a sidebar entry, so it goes to a
    # person regardless of how few lines it is. It has no header to measure
    # from, so it is found by listing upstream rather than by diffing.
    new_pages = sorted(
        name for name in git('ls-tree', '--name-only', head, '--', '*.md').splitlines()
        if name not in NOT_TRANSLATIONS and name not in per_file
    )

    for name in new_pages:
        lines = len(git('show', f'{head}:{name}').splitlines())
        changed.append({'file': name, 'lines': lines, 'base': None,
                        'known': False})

    total = sum(c['lines'] for c in changed)

    if not changed:
        emit({'status': 'current', 'base': base, 'head': head,
              'files': [], 'lines': 0})
        return 0

    routine, oversized, over_budget = select(
        changed, new_pages, args.max_file_lines, args.max_lines,
    )

    if not routine:
        status = 'escalate'
        reason = 'nothing small enough to translate automatically'
    else:
        status = 'translate'
        reason = (f'{sum(c["lines"] for c in routine)} changed lines '
                  f'across {len(routine)} files')

        if over_budget:
            reason += (f'; {len(over_budget)} more deferred to keep the run '
                       f'under {args.max_lines} lines')

    emit({'status': status, 'reason': reason, 'base': base, 'head': head,
          'lines': total, 'files': changed, 'new_pages': new_pages,
          'held': oversized + over_budget, 'oversized': oversized,
          'over_budget': over_budget,
          'translate': [c['file'] for c in routine],
          # Each page travels with the commit it is behind by, because there is
          # no single base any more.
          'bases': {c['file']: c['base'] for c in routine}})

    return 0


def emit(report: dict) -> None:
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if output := os.environ.get('GITHUB_OUTPUT'):
        with open(output, 'a') as handle:
            handle.write(f"status={report['status']}\n")
            handle.write(f"lines={report['lines']}\n")
            handle.write(f"base={report['base']}\n")
            handle.write(f"head={report['head']}\n")
            # `name=sha` pairs: translate_diff.py diffs each page from its own
            # header, so the base cannot be passed once for the whole run.
            bases = report.get('bases', {})
            handle.write('files={}\n'.format(' '.join(
                f'{name}={bases[name]}' for name in report.get('translate', [])
            )))
            handle.write(f"held={' '.join(report.get('held', []))}\n")
            handle.write(f"oversized={' '.join(report.get('oversized', []))}\n")
            handle.write(f"over_budget={' '.join(report.get('over_budget', []))}\n")
            handle.write(f"new_pages={' '.join(report.get('new_pages', []))}\n")

            # Oversized pages and new pages want a person even when the rest of
            # the run translated cleanly, so the workflow opens an issue
            # alongside the pull request. Pages merely over budget do not: no
            # one need read about them, because tomorrow's run picks them up on
            # its own once today's translations have moved their headers.
            needs_person = bool(report.get('oversized') or report.get('new_pages'))
            handle.write(f"needs_person={'true' if needs_person else 'false'}\n")

            if reason := report.get('reason'):
                handle.write(f'reason={reason}\n')


if __name__ == '__main__':
    raise SystemExit(main())
