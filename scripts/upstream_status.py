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
    """The upstream commit each page was translated from, and the common one.

    Pages are normally all on the same commit - the translation moves in one
    sweep - so the oldest is the base for the diff.
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

    # Oldest wins: translating from further back is safe, the reverse is not.
    # Distance is counted towards upstream, so the furthest behind is the max.
    oldest = max(
        set(per_file.values()),
        key=lambda sha: int(git('rev-list', '--count', f'{sha}..upstream/13.x') or 0),
    )

    return oldest, per_file


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

    if base == head:
        report = {'status': 'current', 'base': base, 'head': head,
                  'files': [], 'lines': 0}
        emit(report)
        return 0

    # --numstat over Markdown only: upstream also carries images and licences.
    changed = []
    total = 0

    for row in git('diff', '--numstat', base, head, '--', '*.md').splitlines():
        added, removed, name = row.split('\t')

        if name in NOT_TRANSLATIONS:
            continue

        # Binary files report '-'; upstream has none in *.md, but be safe.
        count = (int(added) if added != '-' else 0) + (int(removed) if removed != '-' else 0)
        changed.append({'file': name, 'lines': count,
                        'known': name in per_file})
        total += count

    # A file upstream has that we have never translated is a new page, not an
    # edit - it needs a title, a slug and a sidebar entry, so it goes to a
    # person regardless of how few lines it is.
    new_pages = [c['file'] for c in changed if not c['known']]

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
          'translate': [c['file'] for c in routine]})

    return 0


def emit(report: dict) -> None:
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if output := os.environ.get('GITHUB_OUTPUT'):
        with open(output, 'a') as handle:
            handle.write(f"status={report['status']}\n")
            handle.write(f"lines={report['lines']}\n")
            handle.write(f"base={report['base']}\n")
            handle.write(f"head={report['head']}\n")
            handle.write(f"files={' '.join(report.get('translate', []))}\n")
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
