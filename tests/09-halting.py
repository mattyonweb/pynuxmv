from pynuxmv.main import *

x = 0
halt: bool = False

while (x < 10):
    x += 1
    if x == 9:
        x = 0

halt = True

ltlspec("F halt")
