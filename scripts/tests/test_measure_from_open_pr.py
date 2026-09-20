#!/usr/bin/env python3
"""Checks that a page already translated on the open branch is left alone.

The run checks out 13.x, where the `git:` headers say whatever was last merged.
While a pull request sits unmerged, the pages on it are translated but their
headers on 13.x have not moved - so every morning the run measured them as
behind and translated them again from scratch.

Retranslating is not idempotent: it is a fresh call to the model, so it comes
back worded differently each time and silently replaced whatever a reviewer had
corrected on the branch. Commit 69a73493 fixed `route` against the glossary on
18 September; the runs of the 19th and 20th each undid it, to two different
wordings ("маршрутизувати ... на чергу", then "направити ... до черги").

Measured from the branch instead, those pages are current and only genuinely
new upstream work is scheduled. On the real PR #25 that was the difference
between 44 lines across 5 pages and 4 lines across 1.

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

        # Upstream: a page, then an edit to it, then an unrelated later edit.
        Path('guide.md').write_text('# Guide\n\nOne.\n')
        Path('other.md').write_text('# Other\n\nOne.\n')
        merged = commit('what 13.x was translated from')

        Path('guide.md').write_text('# Guide\n\nOne.\nTwo.\n')
        translated = commit('what the open branch translated')

        Path('other.md').write_text('# Other\n\nOne.\nTwo.\n')
        head = commit('new upstream work, after the branch')

        # The header as each ref carries it. 13.x still says `merged` for
        # guide.md, because the translation of it is unmerged; the branch says
        # `translated`, because the run that produced the pull request moved it.
        on_13x = {'guide.md': merged, 'other.md': merged}
        on_branch = {'guide.md': translated, 'other.md': merged}

        from_13x = {c['file']: c['lines'] for c in changed_since(on_13x, head)}
        from_branch = {c['file']: c['lines']
                       for c in changed_since(on_branch, head)}

        # The bug: the page on the branch is offered for translation again,
        # and whatever a reviewer fixed on it goes with the retranslation.
        failures += check('from 13.x the reviewed page is scheduled again',
                          'guide.md' in from_13x)

        failures += check('from the branch it is left alone',
                          'guide.md' not in from_branch)

        # Not by skipping work: the genuinely new upstream edit still lands.
        failures += check('new upstream work is still picked up',
                          from_branch.get('other.md') == 1)

        failures += check('so the branch schedules strictly less',
                          sum(from_branch.values()) < sum(from_13x.values()))

        # A branch caught up with upstream has nothing to do at all, which is
        # the quiet case the run hits between upstream commits.
        caught_up = {'guide.md': head, 'other.md': head}

        failures += check('a branch level with upstream schedules nothing',
                          changed_since(caught_up, head) == [])

    print('failures:', failures)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
