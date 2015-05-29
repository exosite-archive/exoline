import yaml
import os

print " ".join(str(x) for x in yaml.load(open(os.path.expanduser("~/.exoline")))['keys'].keys())

