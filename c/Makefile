# UEM-16 C99 — dependency-free (vendored cJSON + sha256 only)
CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror=implicit-function-declaration -O2
CFLAGS += -Iinclude -Ithird_party -Isrc
LDFLAGS ?=

SRC = \
  src/main.c \
  src/decode.c \
  src/machine.c \
  src/primitives.c \
  src/expr.c \
  src/decimal.c \
  third_party/cJSON.c \
  third_party/sha256.c

BUILD = build
BIN = $(BUILD)/uem-c

.PHONY: all clean test asan ubsan vectors

all: $(BIN)

$(BUILD):
	mkdir -p $(BUILD)

$(BIN): $(SRC) include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(SRC) $(LDFLAGS)

clean:
	rm -rf $(BUILD)

asan: CFLAGS += -g -O1 -fsanitize=address -fno-omit-frame-pointer
asan: LDFLAGS += -fsanitize=address
asan: clean all

ubsan: CFLAGS += -g -O1 -fsanitize=undefined -fno-omit-frame-pointer
ubsan: LDFLAGS += -fsanitize=undefined
ubsan: clean all

test: $(BIN)
	./scripts/run_tests.sh

vectors: $(BIN)
	./scripts/gen_golden.sh
	./scripts/diff_py_c.sh
