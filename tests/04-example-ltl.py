from pynuxmv.main import *

a = 0
b = 0
while (a + b < 2):
  if b == 0 and a == 1:
    b = 1  
  else:
    if b == 1 and a == 1:
      b = 0  
  if a == 1:
    a = 0
  else:
    a = 1

ltlspec("F (a = 1 & b = 1)")
ltlspec("(a = 0 & b = 0) -> F (a = 1 & b = 0)")
ltlspec("(a = 1 & b = 0) -> F (a = 0 & b = 1)")
ltlspec("(a = 0 & b = 1) -> F (a = 1 & b = 1)")

