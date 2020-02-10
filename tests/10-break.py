from pynuxmv import *

start_nuxmv()
x = 0
while True:
    x += 1
    if x == 10:
        break
ltlspec("F x = 10")
end_nuxmv()



start_nuxmv()
total, y = 0, 0
for x in range(1, 3):
  y = 0
  while True:
    total += y
    if y == x:
      break
    y += 1  
 
postcondition("total=4", False)
end_nuxmv()



start_nuxmv()
total: bool = True
for x in range(1, 9999999):
  break
  total = False
  
ltlspec("G total", False)
end_nuxmv()



start_nuxmv()
total: bool = True
for x in range(1, 9999999):
    for y in range(29423, 1587624):
        for z in range(99,9999,77):
            break
            total = False
        break
        total = False
    break
    total = False
  
ltlspec("G total", False)
end_nuxmv()
