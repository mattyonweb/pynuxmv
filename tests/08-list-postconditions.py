from pynuxmv.main import *

x = 0
y = 1
l: list = [1,2,3]
while (y < 10):
  x += 1
  y += 1
  y += 0
  l[2] = l[2] + x 

postcondition("y = 10", False)
postcondition("x = 9", False)
postcondition("l[2] = 48", True)
