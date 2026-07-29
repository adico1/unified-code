# UEM-16 C99 — portable core + host adapters
# L12: a target is supported only after native hardware golden pass.
# Coverage objects live in build/*.o so harness and uem-c share .gcda.

CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror=implicit-function-declaration -O2
CFLAGS += -Iinclude -Ithird_party -Icore -Ihost/mcu
LDFLAGS ?=

CORE_SRC = \
  core/alloc.c \
  core/decode.c \
  core/machine.c \
  core/primitives.c \
  core/stateful.c \
  core/expr.c \
  core/decimal.c \
  third_party/cJSON.c \
  third_party/sha256.c

CORE_OBJ = \
  build/alloc.o \
  build/decode.o \
  build/machine.o \
  build/primitives.o \
  build/stateful.o \
  build/expr.o \
  build/decimal.o \
  build/uem_generated_host.o \
  build/cJSON.o \
  build/sha256.o

POSIX_OBJ = build/main.o $(CORE_OBJ)
COV_HARNESS_OBJ = build/core_coverage_harness.o $(CORE_OBJ)

BUILD = build
POSIX_BIN = $(BUILD)/uem-c
COV_BIN = $(BUILD)/core-coverage
MCU_BIN = $(BUILD)/uem-mcu-demo

.PHONY: all clean test asan ubsan posix mcu wasm-compile report l12 coverage-bin

all: posix

posix: $(POSIX_BIN)

mcu: $(MCU_BIN)

coverage-bin: $(POSIX_BIN) $(COV_BIN)

$(BUILD):
	mkdir -p $(BUILD)

build/alloc.o: core/alloc.c core/alloc.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ core/alloc.c
build/decode.o: core/decode.c include/uem.h core/alloc.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ core/decode.c
build/machine.o: core/machine.c include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ core/machine.c
build/primitives.o: core/primitives.c include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ core/primitives.c
build/stateful.o: core/stateful.c include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ core/stateful.c
build/expr.o: core/expr.c include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ core/expr.c
build/decimal.o: core/decimal.c | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ core/decimal.c
build/uem_generated_host.o: ../generated/uem_surface/c/host/generated/uem_generated_host.c include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ ../generated/uem_surface/c/host/generated/uem_generated_host.c
build/cJSON.o: third_party/cJSON.c | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ third_party/cJSON.c
build/sha256.o: third_party/sha256.c | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ third_party/sha256.c
build/main.o: host/posix/main.c include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ host/posix/main.c
build/core_coverage_harness.o: tests/core_coverage_harness.c include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ tests/core_coverage_harness.c

$(POSIX_BIN): $(POSIX_OBJ)
	$(CC) $(CFLAGS) -o $@ $(POSIX_OBJ) $(LDFLAGS)

$(COV_BIN): $(COV_HARNESS_OBJ)
	$(CC) $(CFLAGS) -o $@ $(COV_HARNESS_OBJ) $(LDFLAGS)

$(MCU_BIN): $(MCU_SRC) include/uem.h host/mcu/uem_mcu.h | $(BUILD)
	$(CC) $(CFLAGS) -DUEM_MCU_1 -o $@ host/mcu/mcu_host.c $(CORE_SRC) $(LDFLAGS)

MCU_SRC = host/mcu/mcu_host.c $(CORE_SRC)
WASM_SRC = host/wasm/main.c $(CORE_SRC)

wasm-compile: | $(BUILD)
	@if command -v clang >/dev/null 2>&1; then \
	  clang $(CFLAGS) -DUEM_HOST_WASM -target wasm32-wasi \
	    -o $(BUILD)/uem-core.wasm $(WASM_SRC) $(LDFLAGS) 2>/dev/null \
	    && echo "wasm artifact: $(BUILD)/uem-core.wasm" \
	    || echo "wasm: compile-only unavailable (no wasi sysroot/toolchain)"; \
	else echo "wasm: clang unavailable"; fi

clean:
	rm -rf $(BUILD)
	rm -f *.gcov core/*.gcov

asan: CFLAGS += -g -O1 -fsanitize=address -fno-omit-frame-pointer
asan: LDFLAGS += -fsanitize=address
asan: clean posix

ubsan: CFLAGS += -g -O1 -fsanitize=undefined -fno-omit-frame-pointer
ubsan: LDFLAGS += -fsanitize=undefined
ubsan: clean posix

test: posix
	./scripts/diff_py_c.sh
	UEM_C=$(CURDIR)/$(POSIX_BIN) ../.venv/bin/python -c "from unified.machine.l11 import run_l11_gauntlet; from unified.machine.thing import value_of as v; r=run_l11_gauntlet(); assert v(r)['l11']['verdict']=='pass'"

l12: posix
	../.venv/bin/python scripts/run_l12_report.py

report: l12
