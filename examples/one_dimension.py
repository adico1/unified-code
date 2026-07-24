from unified import letter, line, verify


def program(thing):
    return verify(line(letter(thing)))


print(program("seed"))
