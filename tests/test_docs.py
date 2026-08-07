from pathlib import Path
from textwrap import dedent

from gitfame import _gitfame


def test_readme():
    doc = '    Usage:\n'
    with (Path(__file__).parent.parent / 'README.rst').open(encoding='utf-8') as f:
        while f.readline() != doc:
            pass
        while True:
            line = f.readline()
            if line.startswith(' ' * 4) or line == "\n":
                doc += line
            else:
                break
    assert dedent(doc).strip() == _gitfame.__doc__.strip()
