import os
from modules.rayfunc import *

for file in os.listdir('test'):
    f = os.path.join('test', file)
    if not os.path.isfile(f):
        continue
    print("testing: " + f)
    print(cfgtolink(f, "testing", "1.1.1.1", "9c632f3f-197a-4d10-4c0d-61f50fd206c8", "0", "none"))
