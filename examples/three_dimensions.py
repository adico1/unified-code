from unified import letter, space, verify, world


def program(thing):
    return world(verify(space(letter(thing))))


print(program("seed"))
