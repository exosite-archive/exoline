from exoline import exo
import re

for k,v in exo.cmd_doc.iteritems():
	print k, re.findall(r"(--\w.*)[^=<> ]", v.replace("\t", " "))