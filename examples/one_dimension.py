from unified import inward, letter, line, verify


def program(thing):
    return verify(line(letter(inward(thing))))


if __name__ == "__main__":
    from unified import host_render, outward

    print(host_render(outward(program("seed"))))
