# zerobas — build the 16 KB cartridge ROM.
#
# Requires pasmo (the assembler C-BIOS uses). Build from the repo root so the
# `include` paths in src/main.asm resolve.

PASMO ?= pasmo
SRC   := src/main.asm
DEPS  := src/bload.asm src/sysvars.inc
ROM   := basic.rom

$(ROM): $(SRC) $(DEPS)
	$(PASMO) --bin $(SRC) $(ROM)
	python3 tools/pad_rom.py $(ROM) 16384

clean:
	rm -f $(ROM)

.PHONY: clean
