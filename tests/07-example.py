i = 0
b: bool = False #annotation necessary bc otherwise type is set automatically to integer!

while (not (b == True)):
  i += 1
  if i == 5:
    b = True

ltlspec("F i = 5")
invarspec("i < 5 -> !b")
