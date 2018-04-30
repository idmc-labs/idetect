from sqlalchemy import *
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Executable, ClauseElement, _literal_as_text

class explain(Executable, ClauseElement):
    def __init__(self, stmt, analyze=False):
        self.statement = _literal_as_text(stmt)
        self.analyze = analyze
        # helps with INSERT statements
        self.inline = getattr(stmt, 'inline', None)

@compiles(explain, 'postgresql')
def pg_explain(element, compiler, **kw):
    text = "EXPLAIN "
    if element.analyze:
        text += "ANALYZE "
    text += compiler.process(element.statement, **kw)
    return text

def explain_text(session, query):
    plan = session.execute(explain(query)).fetchall()
    lines = [r[0] for r in plan]
    return "\n".join(lines)
