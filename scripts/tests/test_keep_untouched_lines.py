#!/usr/bin/env python3
"""Checks that restyling of untouched lines is reverted.

The model is handed a whole section and returns a whole section, so lines the
diff never mentioned still pass through it and keep coming back reworded. The
cases below are the real ones from the 5e0a0edf sync, where the translator
rewrote settled prose in collections.md, horizon.md, pint.md and dusk.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translate_diff import keep_untouched_lines

CASES = [
    # (name, current, translated, diff, expected)
    (
        'reverts a synonym swap the diff did not ask for',
        'Метод `crossJoin` повертає декартів добуток з усіма можливими поєднаннями:',
        'Метод `crossJoin` повертає декартів добуток з усіма можливими комбінаціями:',
        '',
        'Метод `crossJoin` повертає декартів добуток з усіма можливими поєднаннями:',
    ),
    (
        'reverts a reworded opening clause',
        'Якщо ви хочете використовувати атрибут nonce, скористайтеся `Horizon::cspNonce`.',
        'Якщо ви хотіли б використовувати атрибут nonce, скористайтеся `Horizon::cspNonce`.',
        '',
        'Якщо ви хочете використовувати атрибут nonce, скористайтеся `Horizon::cspNonce`.',
    ),
    (
        'keeps a line the diff actually changed',
        'Ви можете вилучити cookie методом `withoutCookie`:',
        'Ви можете вилучити cookie методом `withoutCookie` або `withoutCookies`:',
        '-You may remove a cookie with the `withoutCookie` method:\n'
        '+You may remove a cookie with the `withoutCookie` or `withoutCookies` method:',
        'Ви можете вилучити cookie методом `withoutCookie` або `withoutCookies`:',
    ),
    (
        'leaves output alone when the model changed the line count',
        'Один рядок.',
        'Перший рядок.\nДругий рядок.',
        '',
        'Перший рядок.\nДругий рядок.',
    ),
]


def main() -> int:
    failures = 0

    for name, current, translated, diff, expected in CASES:
        actual = keep_untouched_lines(current, translated, diff)

        if actual != expected:
            print(f'  {name}:', file=sys.stderr)
            print(f'    expected: {expected!r}', file=sys.stderr)
            print(f'    actual:   {actual!r}', file=sys.stderr)
            failures += 1

    # A multi-line section: only the line whose English changed may move.
    current = (
        'Перший абзац лишається незмінним.\n'
        'Ви можете вилучити cookie методом `withoutCookie`:\n'
        'Третій абзац теж лишається.'
    )
    translated = (
        'Перший абзац залишається без змін.\n'
        'Ви можете вилучити cookie методом `withoutCookie` або `withoutCookies`:\n'
        'Третій абзац також лишається.'
    )
    diff = ('-You may remove a cookie with the `withoutCookie` method:\n'
            '+You may remove a cookie with the `withoutCookie` or `withoutCookies` method:')

    result = keep_untouched_lines(current, translated, diff).splitlines()

    if result[0] != 'Перший абзац лишається незмінним.':
        print('  multi-line: first line was not reverted', file=sys.stderr)
        failures += 1

    if '`withoutCookies`' not in result[1]:
        print('  multi-line: the changed line was reverted', file=sys.stderr)
        failures += 1

    if result[2] != 'Третій абзац теж лишається.':
        print('  multi-line: third line was not reverted', file=sys.stderr)
        failures += 1

    print('keep_untouched_lines failures:', failures)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
