from exoline import exo
import sys
import re

print sys.argv


doc=exo.cmd_doc.get(sys.argv[-1], "")

print " ".join(set(r for r in re.findall(r"(--\w+[^= \n()<>])", doc) if r.startswith("-")))
