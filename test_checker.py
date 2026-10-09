from pathlib import Path
from tempfile import TemporaryDirectory
from app.checker import static_check, conservative_fix

def test_python_syntax_issue():
    with TemporaryDirectory() as d:
        p = Path(d)/'x.py'; p.write_text('def x(:\n    pass\n', encoding='utf-8')
        issues = static_check(p)
        assert issues

def test_conservative_fix():
    with TemporaryDirectory() as d:
        p=Path(d)/'x.py'; p.write_text('print("x")  \r\n', encoding='utf-8')
        assert conservative_fix(p) == 1
        assert p.read_text(encoding='utf-8') == 'print("x")\n'
