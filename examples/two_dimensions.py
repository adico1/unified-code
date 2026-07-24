from unified import letter, plane, verify


def program(thing):
    return verify(plane(letter(thing)))


print(program("seed"))
