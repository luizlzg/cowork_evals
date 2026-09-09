"""The trivial failing case that fails for the right reason.

`except*` is Python 3.11 grammar. The CoWork runtime is 3.10, so this file does not parse
there and pytest exits 2 on the collection error. That is the fixture: a suite written
against a newer interpreter than a session has fails here rather than passing on a laptop
and failing in a session.

It is a syntax error on the interpreter it runs on, so it can never be collected alongside
another file. The integration tier runs it alone.
"""


def test_the_grammar_is_3_11():
    caught = False
    try:
        raise ExceptionGroup("group", [ValueError("x")])
    except* ValueError:
        caught = True
    assert caught
