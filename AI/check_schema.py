from database import engine
from sqlalchemy import inspect

insp = inspect(engine)
cols = insp.get_columns("scripts")
for c in cols:
    name = c["name"]
    ctype = str(c["type"])
    nullable = c["nullable"]
    default = c.get("default")
    print(f"{name:20s} {ctype:20s} nullable={nullable}  default={default}")
