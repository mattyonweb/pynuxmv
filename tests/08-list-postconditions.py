from pynuxmv.main import *

x = 0
y = 1
l: list = [1,2,3]
while (y < 5):
  x += 1
  y += 1
  l[2] = l[2] + x 

postcondition("y = 5", False)
postcondition("x = 4", False)
postcondition("l[2] = 13", True)
