# Known failures

Failing checks that show a bug in `src/`, kept failing until the bug is fixed. `tools/check.py`
reports them apart and does not fail the gate on them; a known test that passes again is
reported, and its row comes out of this table. The first column is the test name (as in
`test( "..." )` in `tests/*.c`) or a check key (`sim:...`, `perf:...` from `tools/check.py`).

| Check | What is wrong | Suspected line |
|---|---|---|
