from pynuxmv.main import *

i = 28

for x in range(10, 2, -2):
    i += -x

ltlspec("F i = 0")
