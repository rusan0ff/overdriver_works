import sqlite3, sys
print('py', sys.version.split()[0])
c = sqlite3.connect(':memory:')
try:
    c.execute('CREATE VIRTUAL TABLE t USING fts5(x)')
    c.execute("INSERT INTO t VALUES ('hello world')")
    n = c.execute("SELECT count(*) FROM t WHERE t MATCH 'hello'").fetchone()[0]
    print('fts5 ok:', n)
except Exception as e:
    print('fts5 FAIL:', type(e).__name__, e)
