#!/usr/bin/env python3
"""Checks that a run over budget clears what it can afford instead of nothing.

Issue #11 reported thirty-seven pages as "too large for automation" when only
one of them was: head.md at 762 changed lines, and behind it thirty-six pages
of one and two line fixes whose 472 lines together overran the 400-line budget.
The overflow branch discarded the lot, so nothing translated, no `git:` header
moved, and the next day's diff spanned the same commits and overran again - the
sync stood still for weeks with a queue it could have cleared most of on any
morning.

No API key and no git: what broke is the arithmetic in front of the model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upstream_status import select


def page(name: str, lines: int, known: bool = True) -> dict:
    return {'file': name, 'lines': lines, 'known': known}


def check(name: str, condition: bool) -> int:
    print(('  ok  ' if condition else '  FAIL') + f' {name}')

    return 0 if condition else 1


def main() -> int:
    failures = 0

    # The shape of issue #11: one page far over the per-file limit, and a tail
    # of small ones that together exceed the run budget.
    changed = [page('head.md', 762), page('boost.md', 93), page('pint.md', 37)]
    changed += [page(f'small{i}.md', 2) for i in range(20)]

    routine, oversized, over_budget = select(
        changed, new_pages=[], max_file_lines=150, max_lines=100,
    )
    names = [c['file'] for c in routine]

    failures += check('the oversized page is held on its own',
                      oversized == ['head.md'])
    failures += check('head.md is not offered for translation',
                      'head.md' not in names)
    failures += check('the budget is spent, not abandoned', routine != [])
    failures += check('the budget is respected',
                      sum(c['lines'] for c in routine) <= 100)

    # Smallest first: the twenty 2-line pages cost 40 and pint.md's 37 fits in
    # what is left, for 21 of the 22 eligible pages. Taken in diff order
    # instead, boost.md's 93 would have eaten almost the whole budget first.
    failures += check('small pages are preferred', len(routine) == 21)
    failures += check('what did not fit is reported separately',
                      over_budget == ['boost.md'])
    failures += check('over-budget pages are not called oversized',
                      'boost.md' not in oversized)

    # Every page is accounted for exactly once, or a file silently vanishes
    # from the run and no one is told.
    seen = names + oversized + over_budget
    failures += check('every changed page is accounted for once',
                      sorted(seen) == sorted(c['file'] for c in changed))

    # Order follows the diff, not the size the selection sorted by: the list
    # travels to translate_diff.py as arguments.
    failures += check('the diff order is restored',
                      names == [c['file'] for c in changed
                                if c['file'] in set(names)])

    # A run that fits needs no deferral at all.
    routine, oversized, over_budget = select(
        [page('a.md', 10), page('b.md', 20)], [], 150, 400,
    )

    failures += check('a run within budget defers nothing',
                      over_budget == [] and oversized == []
                      and len(routine) == 2)

    # A page upstream has and we do not is a new page: it wants a person for
    # its slug and sidebar entry, and must not be spent from the budget.
    routine, oversized, over_budget = select(
        [page('a.md', 10), page('brand-new.md', 10, known=False)],
        new_pages=['brand-new.md'], max_file_lines=150, max_lines=400,
    )
    names = [c['file'] for c in routine]

    failures += check('a new page is not translated',
                      names == ['a.md'])
    failures += check('a new page is not mistaken for over budget',
                      over_budget == [])

    # The pathological case: a single page below the per-file limit but above
    # the whole run's budget. It must not be silently dropped - it is over
    # budget and reported, not translated.
    routine, oversized, over_budget = select(
        [page('one.md', 120)], [], max_file_lines=150, max_lines=100,
    )

    failures += check('a page over the run budget alone is reported',
                      routine == [] and over_budget == ['one.md'])

    print('failures:', failures)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
