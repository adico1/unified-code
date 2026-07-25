# UEM-16 C99 — portable core + host adapters
# L12: a target is supported only after native hardware golden pass.

CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror=implicit-function-declaration -O2
CFLAGS += -Iinclude -Ithird_party -Icore -Ihost/mcu
LDFLAGS ?=

CORE_SRC = \
  core/decode.c \
  core/machine.c \
  core/primitives.c \
  core/expr.c \
  core/decimal.c \
  third_party/cJSON.c \
  third_party/sha256.c

POSIX_SRC = host/posix/main.c $(CORE_SRC)
WASM_SRC  = host/wasm/main.c $(CORE_SRC)
MCU_SRC   = host/mcu/mcu_host.c $(CORE_SRC)

BUILD = build
POSIX_BIN = $(BUILD)/uem-c
MCU_BIN   = $(BUILD)/uem-mcu-demo

.PHONY: all clean test asan ubsan posix mcu wasm-compile report l12

all: posix

posix: $(POSIX_BIN)

mcu: $(MCU_BIN)

$(BUILD):
	mkdir -p $(BUILD)

$(POSIX_BIN): $(POSIX_SRC) include/uem.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(POSIX_SRC) $(LDFLAGS)

$(MCU_BIN): $(MCU_SRC) include/uem.h host/mcu/uem_mcu.h | $(BUILD)
	$(CC) $(CFLAGS) -DUEM_MCU_1 -o $@ $(MCU_SRC) $(LDFLAGS)

# Wasm: compile-only unless WASI toolchain present
wasm-compile: | $(BUILD)
	@if command -v clang >/dev/null 2>&1; then \
	  clang $(CFLAGS) -DUEM_HOST_WASM -target wasm32-wasi \
	    -o $(BUILD)/uem-core.wasm $(WASM_SRC) $(LDFLAGS) 2>/dev/null \
	    && echo "wasm artifact: $(BUILD)/uem-core.wasm" \
	    || echo "wasm: compile-only unavailable (no wasi sysroot/toolchain)"; \
	else echo "wasm: clang unavailable"; fi

clean:
	rm -rf $(BUILD)

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
