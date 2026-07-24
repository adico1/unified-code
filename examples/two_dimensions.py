from unified import inward, letter, plane, verify


def program(thing):
    return verify(plane(letter(inward(thing))))


if __name__ == "__main__":
    from unified import host_render, outward

    print(host_render(outward(program("seed"))))
