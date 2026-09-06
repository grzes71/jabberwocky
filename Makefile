# Makefile — Jabberwocky
# Atari 800 XL / 65 XE

# ---- Narzędzia ----
MADS      ?= c:/Apps/Mad-Assembler-2.1.6/bin/windows_x86_64/mads.exe
ALTIRRA   ?= C:/Apps/Altirra-4.40/Altirra64.exe

ifeq ($(wildcard $(CURDIR)/.venv/Scripts/python.exe),)
    PYTHON ?= python
else
    PYTHON ?= $(CURDIR)/.venv/Scripts/python.exe
endif

# ---- Cross-platform: wykrywanie OS ----
ifeq ($(OS),Windows_NT)
    RM    := cmd /c del /q
    RMDIR := cmd /c rmdir /s /q
    MKDIR := mkdir
else
    RM    := rm -f
    RMDIR := rm -rf
    MKDIR := mkdir -p
endif

# ---- Pliki ----
ASM_MAIN       := main.asm
ASM_HW         := hardware.asm
ASM_ZP         := zeropage.asm
ASM_SCENES     := $(wildcard scenes/*.asm)
XEX_OUT        := jabberwocky.xex
GEN_DIR        := gen

IMG_TITLE      := img/title.png
TITLE_BIN      := $(GEN_DIR)/title.bin
CONVERT_SCRIPT := scripts/convert_image.py

# ---- Cele ----
.PHONY: all xex clean run help

all: $(XEX_OUT)

xex: $(XEX_OUT)

$(TITLE_BIN): $(IMG_TITLE) $(CONVERT_SCRIPT)
	@echo === Konwersja $(IMG_TITLE) do $(TITLE_BIN) (atari-image-converter, ANTIC F 320x175) ===
	$(PYTHON) $(CONVERT_SCRIPT) -i $(IMG_TITLE) -o $(TITLE_BIN) --width 320 --height 175 --mode F

$(XEX_OUT): $(ASM_MAIN) $(ASM_HW) $(ASM_ZP) $(ASM_SCENES) $(TITLE_BIN)
	@echo === Asemblacja $(ASM_MAIN) do $(XEX_OUT) (MADS) ===
	$(MADS) $(ASM_MAIN) -o:$(XEX_OUT) -l:$(GEN_DIR)/jabberwocky.lst -t:$(GEN_DIR)/jabberwocky.lab

run: $(XEX_OUT)
	@echo === Uruchamianie w emulatorze Altirra ===
	$(ALTIRRA) $(XEX_OUT)

clean:
	@echo === Sprzątanie plików wygenerowanych ===
ifeq ($(OS),Windows_NT)
	-@cmd /c if exist $(XEX_OUT) del /q /f $(XEX_OUT)
	-@cmd /c if exist $(GEN_DIR) rmdir /s /q $(GEN_DIR)
else
	-rm -f $(XEX_OUT)
	-rm -rf $(GEN_DIR)
endif

help:
	@echo Dostępne cele:
	@echo   make        - buduje obraz tła i kompiluje $(XEX_OUT)
	@echo   make clean  - usuwa wygenerowane pliki ($(XEX_OUT), $(GEN_DIR)/)
	@echo   make run    - uruchamia $(XEX_OUT) w Altirra
	@echo   make help   - ta pomoc
