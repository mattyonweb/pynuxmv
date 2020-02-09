i = 0
j = 0
while (i < 10):
    i += 1
    if (i < 3):
        j = j + 1
invarspec("j < 3")
invarspec("i <= 10")
