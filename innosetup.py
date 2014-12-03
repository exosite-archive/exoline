# update Exoline version number in innosetup.iss
# for Windows installer

import exoline
outlines = []
with open('innosetup.iss') as f:    
    for l in f.readlines():
        if l.startswith('AppVersion='):
            outlines.append('AppVersion=' + exoline.__version__ + '\r\n')
        else:
            outlines.append(l)

with open('innosetup.iss', 'w') as f:
    f.write(''.join(outlines))
