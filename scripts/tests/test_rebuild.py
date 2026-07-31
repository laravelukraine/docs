#!/usr/bin/env python3
"""Checks that a section upstream added reaches the translated page.

Run #7 failed on telescope.md and validation.md because the rebuild walked our
own sections: an anchor upstream had just introduced matched nothing here, so
it was never visited and never written. The page came out short by exactly the
new section and the validator rejected it for a dropped anchor - a report that
described the symptom and not the cause.

No API key and no git: the model is a stub, because what broke was the
assembly around it, not the translation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translate_diff import rebuild

# The `git:` header is exactly three lines with no blank after it, which is the
# "+3" the validator's line-count check is built on.
CURRENT = """\
---
git: 0000000000000000000000000000000000000000
---
# Телескоп

<a name="intro"></a>
## Вступ

Текст.

<a name="pruning"></a>
## Очищення

Текст.
"""

# Upstream has gained a section between the two, exactly as telescope.md did.
UPSTREAM = """\
# Telescope

<a name="intro"></a>
## Intro

Text.

<a name="csp-nonce"></a>
## CSP Nonce

Text.

<a name="pruning"></a>
## Pruning

Text.
"""


def translated(anchor: str, section: str) -> str:
    """Stand in for the model: same shape, marked so we can see its origin."""
    return section.replace('Text.', 'Текст.').strip('\n')


def check(name: str, condition: bool) -> int:
    print(('  ok  ' if condition else '  FAIL') + f' {name}')

    return 0 if condition else 1


def main() -> int:
    failures = 0

    page, added, deferred = rebuild(
        CURRENT, UPSTREAM, {'csp-nonce'}, translated, translated,
    )

    failures += check('the new section is added', added == ['csp-nonce'])
    failures += check('nothing is deferred', deferred == [])
    failures += check('the new anchor is on the page',
                      '<a name="csp-nonce"></a>' in page)
    failures += check('it lands between the sections it does upstream',
                      page.index('csp-nonce') < page.index('pruning'))
    failures += check('untouched sections are kept verbatim',
                      '## Вступ' in page and '## Очищення' in page)
    failures += check('the header survives', page.startswith('---\ngit: '))

    # The line count is what the validator checks, and the whole point of the
    # exercise: our three header lines on top of upstream's.
    expected = len(UPSTREAM.splitlines()) + 3
    failures += check(f'line count is {expected}',
                      len(page.splitlines()) == expected)

    # A section upstream dropped must not linger here, or validation rejects
    # the page for an invented anchor.
    shrunk = UPSTREAM.replace('<a name="pruning"></a>\n## Pruning\n\nText.\n', '')
    page, _, _ = rebuild(CURRENT, shrunk, set(), translated, translated)

    failures += check('a section upstream removed is dropped',
                      'Очищення' not in page)

    # A new section the model declines leaves the page short rather than
    # wrong, and says so.
    page, added, deferred = rebuild(
        CURRENT, UPSTREAM, {'csp-nonce'}, translated, lambda a, s: None,
    )

    failures += check('a declined new section is reported',
                      added == [] and deferred == ['csp-nonce'])

    print('failures:', failures)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
