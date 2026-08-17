#!/usr/bin/env python3
"""Checks that each page is measured from its own `git:` header.

The run used to diff every page from one shared base - the oldest header in the
translation. Any page ahead of that base was then diffed across commits it had
already been brought through, and the edits it already carried were offered for
translation again.

head.md is how this surfaced. It had been translated by hand and its header was
current, but the shared base predated the file's existence upstream, so all 762
of its lines counted as pending and it was filed as "too large for automation"
every morning. Measured from its own header it had nothing to do at all - and
across the whole translation the shared base inflated 73 real changed lines
into 1234.

Builds a throwaway repository rather than leaning on this one, so the test says
the same thing after the real pages move on.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upstream_status import changed_since


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def commit(message: str) -> str:
    git('add', '-A')
    git('commit', '--quiet', '-m', message)

    return git('rev-parse', 'HEAD')


def check(name: str, condition: bool) -> int:
    print(('  ok  ' if condition else '  FAIL') + f' {name}')

    return 0 if condition else 1


def main() -> int:
    failures = 0

    with tempfile.TemporaryDirectory() as work:
        os.chdir(work)
        git('init', '--quiet', '-b', 'main')
        git('config', 'user.email', 'test@example.com')
        git('config', 'user.name', 'test')

        # Upstream at its first commit: one page.
        Path('early.md').write_text('# Early\n\nOne.\n')
        first = commit('first')

        # Later upstream edits that page and adds a second one - the shape that
        # broke head.md, which upstream added after our oldest header.
        Path('early.md').write_text('# Early\n\nOne.\nTwo.\n')
        Path('late.md').write_text('# Late\n\n' + 'Line.\n' * 40)
        head = commit('second')

        # early.md is behind; late.md was translated by hand at the newer
        # commit and is already current.
        per_file = {'early.md': first, 'late.md': head}

        changed = changed_since(per_file, head)
        by_name = {c['file']: c for c in changed}

        failures += check('a page on the newest commit has nothing to do',
                          'late.md' not in by_name)
        failures += check('a page behind is reported', 'early.md' in by_name)
        failures += check('it carries its own base as the diff base',
                          by_name['early.md']['base'] == first)
        failures += check('only the real change is counted',
                          by_name['early.md']['lines'] == 1)

        # The bug itself: measured from the older shared base, the current page
        # reports its whole length as pending.
        shared = changed_since({'early.md': first, 'late.md': first}, head)
        inflated = {c['file']: c['lines'] for c in shared}

        failures += check('a shared base would have invented work',
                          inflated.get('late.md') == 42)
        failures += check('and the per-file base does not',
                          sum(c['lines'] for c in changed)
                          < sum(c['lines'] for c in shared))

        # Nothing behind at all is the quiet everyday case.
        failures += check('a translation fully caught up reports nothing',
                          changed_since({'early.md': head, 'late.md': head},
                                        head) == [])

    print('failures:', failures)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
