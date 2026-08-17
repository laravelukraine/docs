#!/usr/bin/env python3
"""Checks what a page that fails validation costs the run.

Run #13 translated thirty-odd files correctly and opened no pull request: one
section of installation.md came back two lines short, and the script exited 1
on it, so the branch step never ran and every good translation was thrown away.

Two behaviours are pinned here. A page that fails is built again, because the
usual cause is a model dropping a blank line and asking twice usually fixes it.
A page that fails both times is left exactly as it was - old `git:` header
included, so the next run retries it - and the run still succeeds, carrying the
pages that did validate.

Runs against a real temporary git repository, because main() reads upstream
through `git show`. The model is a stub; nothing here reaches the network.
"""
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# main() imports the SDK and constructs a client before it does any work. The
# calls that would use it are stubbed below, so a placeholder module is enough
# and this test runs without `pip install anthropic`, like its neighbours.
stub_sdk = types.ModuleType('anthropic')
stub_sdk.Anthropic = lambda *args, **kwargs: None
sys.modules.setdefault('anthropic', stub_sdk)

import translate_diff

BASE_PAGE = """\
# Installation

<a name="intro"></a>
## Intro

Text.

<a name="ide-support"></a>
## IDE Support

One paragraph.
"""

# Upstream grows the section, exactly as installation.md did: a paragraph, a
# fenced block, and the blank lines between them.
HEAD_PAGE = """\
# Installation

<a name="intro"></a>
## Intro

Text.

<a name="ide-support"></a>
## IDE Support

One paragraph.

Install it globally:

```shell
composer global require laravel/lsp
```
"""

TRANSLATION = """\
---
git: {base}
---
# Встановлення

<a name="intro"></a>
## Вступ

Текст.

<a name="ide-support"></a>
## Підтримка IDE

Один абзац.
"""


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def build_repo(root: Path) -> tuple[str, str]:
    """A repository with the page before and after the upstream change."""
    git('init', '--quiet', '-b', 'main', str(root))
    os.chdir(root)
    git('config', 'user.email', 'test@example.com')
    git('config', 'user.name', 'test')

    (root / 'GLOSSARY.md').write_text('глосарій\n')
    (root / 'installation.md').write_text(BASE_PAGE)
    git('add', '-A')
    git('commit', '--quiet', '-m', 'base')
    base = git('rev-parse', 'HEAD')

    (root / 'installation.md').write_text(HEAD_PAGE)
    git('add', '-A')
    git('commit', '--quiet', '-m', 'head')
    head = git('rev-parse', 'HEAD')

    # The translation is a working-tree file, not a commit: that is how the
    # real script finds it.
    (root / 'installation.md').write_text(TRANSLATION.format(base=base))

    return base, head


class Stub:
    """Stands in for the Anthropic client.

    A real call gets the current translation plus the diff and returns the
    section brought up to date; this returns the expected Ukrainian directly.
    The first `bad` calls come back short by one line - the shape of the
    failure being retried.
    """

    GOOD = """\
<a name="ide-support"></a>
## Підтримка IDE

Один абзац.

Встановіть глобально:

```shell
composer global require laravel/lsp
```
"""

    def __init__(self, bad: int) -> None:
        self.bad = bad
        self.calls = 0

    def translate(self) -> str:
        self.calls += 1

        if self.calls <= self.bad:
            # Drop the blank line before the fence. It is interior to the
            # section, so restore_edges cannot put it back - which is exactly
            # why the page has to be built again.
            return self.GOOD.replace('\n\n```shell', '\n```shell')

        return self.GOOD


def run(bad: int) -> tuple[int, str, int]:
    """Run main() with a stubbed model. Returns exit code, page, call count."""
    stub = Stub(bad)

    translate_diff.translate = lambda client, glossary, current, diff: \
        stub.translate()
    translate_diff.translate_new = lambda client, glossary, section: \
        stub.translate()

    root = Path(tempfile.mkdtemp())
    base, head = build_repo(root)

    sys.argv = ['translate_diff.py', f'installation.md={base}',
                '--head', head]

    code = translate_diff.main()

    return code, (root / 'installation.md').read_text(), stub.calls


def check(name: str, condition: bool) -> int:
    print(('  ok  ' if condition else '  FAIL') + f' {name}')

    return 0 if condition else 1


def main() -> int:
    failures = 0
    origin = Path.cwd()

    # main() imports the SDK and refuses without a key; neither is reached
    # because the two functions that call the client are stubbed above.
    os.environ.setdefault('ANTHROPIC_API_KEY', 'test')

    try:
        # One bad response, then a good one: the retry saves the page.
        code, page, calls = run(bad=1)

        failures += check('a retried page succeeds', code == 0)
        failures += check('the retry actually happened', calls == 2)
        failures += check('the good translation is written',
                          'Встановіть глобально:' in page)
        failures += check('the header moves to the new commit',
                          'git: 0000' not in page)

        # Every attempt bad: the page is left alone and the run still passes.
        code, page, calls = run(bad=99)

        failures += check('a page failing every attempt does not fail the run',
                          code == 0)
        failures += check('it is tried ATTEMPTS times',
                          calls == translate_diff.ATTEMPTS)
        failures += check('the page is left untouched',
                          page.endswith('Один абзац.\n')
                          and 'Встановіть глобально' not in page)

        # The old header is what makes the next run pick it up again.
        failures += check('its header still points at the old commit',
                          'Підтримка IDE' in page)
    finally:
        os.chdir(origin)

    print('failures:', failures)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
