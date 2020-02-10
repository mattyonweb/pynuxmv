""" Here we test some assignments. """
from pynuxmv import *

a = 1
a, b, c = a-1, 5, 10
l: list = [1,2,3]
l[2] = 99
l[1] = c
d, l[a] = 7, 42

total = 0
for x in range(5):
  y = 0
  while y < x:
    y += 1
  total += y


ltlspec("F (l[2] = 99)")
ltlspec("F (l[1] = 10)")
ltlspec("F (l[0] = 42)")
postcondition("(total = 10)", False)
ltlspec("F (a = 0 & b = 5 & c = 10)")
