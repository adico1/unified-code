from unified import inward, letter, space, verify, world


def program(thing):
    return world(verify(space(letter(inward(thing)))))


if __name__ == "__main__":
    from unified import host_render, outward

    print(host_render(outward(program("seed"))))
