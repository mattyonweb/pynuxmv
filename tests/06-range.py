from pynuxmv.main import *

start_nuxmv()
i = 28
for x in range(10, 2, -2):
    i += -x

ltlspec("F i = 0")
end_nuxmv()

start_nuxmv()
i = 0
for x in range(0, 10, 1+1):
    i += x
ltlspec("F i = 20")
end_nuxmv()
