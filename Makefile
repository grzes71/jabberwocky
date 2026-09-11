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
FONT_DEFAULT   := fonts/text.fnt
TEXT_TITLE     := texts/title.txt
XEX_OUT        := jabberwocky.xex
GEN_DIR        := gen

IMG_TITLE      := img/title.png
TITLE_BIN      := $(GEN_DIR)/title.bin
CONVERT_SCRIPT := scripts/convert_image.py

SPRITE_JSON    := sprites/jabberwocky.json
DRAGON_ASM     := $(GEN_DIR)/dragon_sprite.asm
SPRITE_SCRIPT  := scripts/compile_sprites.py

# ---- Cele ----
.PHONY: all xex data check_memory clean run test help

all: $(XEX_OUT) check_memory

xex: $(XEX_OUT)

MAP_SCRIPT     := scripts/generate_memory_map.py
DOCS_DIR       := docs
MAP_TXT        := $(DOCS_DIR)/memory_map.txt
MAP_JSON       := $(DOCS_DIR)/memory_map.json

TEXT_DIR       := texts
TEXT_SRC       := $(wildcard $(TEXT_DIR)/*.txt)
TEXT_SCRIPT    := scripts/compile_texts.py
TEXT_GEN_ASM   := $(GEN_DIR)/intro_text.asm $(GEN_DIR)/title_scroll_text.asm

$(TEXT_GEN_ASM): $(TEXT_SRC) $(TEXT_SCRIPT)
	@echo === Kompilacja tekstów $(TEXT_DIR)/ do $(GEN_DIR)/ (scripts/compile_texts.py) ===
	$(PYTHON) $(TEXT_SCRIPT) --texts-dir $(TEXT_DIR) --gen-dir $(GEN_DIR)

$(TITLE_BIN): $(IMG_TITLE) $(CONVERT_SCRIPT)
	@echo === Konwersja $(IMG_TITLE) do $(TITLE_BIN) (atari-image-converter, ANTIC F 320x175) ===
	$(PYTHON) $(CONVERT_SCRIPT) -i $(IMG_TITLE) -o $(TITLE_BIN) --width 320 --height 175 --mode F

$(DRAGON_ASM): $(SPRITE_JSON) $(SPRITE_SCRIPT)
	@echo === Kompilacja sprajta $(SPRITE_JSON) do $(DRAGON_ASM) ===
	$(PYTHON) $(SPRITE_SCRIPT) -i $(SPRITE_JSON) -o $(DRAGON_ASM)

PROJECT_YAML    := world/project.yaml
OBJECTS_YAML    := world/objects.yaml
COLORS_YAML     := world/colors.yaml
WORLD_SCRIPT    := scripts/labirynt_builder.py
WORLD_GEN_ASM   := $(GEN_DIR)/world_data.asm
FONT_GAME       := fonts/game.fnt

data: $(WORLD_GEN_ASM)

$(WORLD_GEN_ASM): $(PROJECT_YAML) $(OBJECTS_YAML) $(COLORS_YAML) $(WORLD_SCRIPT)
	@echo === Kompilacja swiata $(PROJECT_YAML) do $(WORLD_GEN_ASM) (scripts/labirynt_builder.py) ===
	$(PYTHON) $(WORLD_SCRIPT) --project $(PROJECT_YAML) --objects $(OBJECTS_YAML) --colors $(COLORS_YAML) --output $(WORLD_GEN_ASM)

$(XEX_OUT): $(ASM_MAIN) $(ASM_HW) $(ASM_ZP) $(ASM_SCENES) $(FONT_DEFAULT) $(FONT_GAME) $(TITLE_BIN) $(DRAGON_ASM) $(TEXT_GEN_ASM) $(WORLD_GEN_ASM)
	@echo === Asemblacja $(ASM_MAIN) do $(XEX_OUT) (MADS) ===
	$(MADS) $(ASM_MAIN) -o:$(XEX_OUT) -l:$(GEN_DIR)/jabberwocky.lst -t:$(GEN_DIR)/jabberwocky.lab

check_memory: $(XEX_OUT) $(MAP_SCRIPT)
	@echo === Weryfikacja i generowanie mapy pamieci ===
	$(PYTHON) $(MAP_SCRIPT) --input $(GEN_DIR)/jabberwocky.lab --out-text $(MAP_TXT) --out-json $(MAP_JSON)

test:
	@echo === Uruchamianie testow pytest ===
	$(PYTHON) -m pytest tests -v

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
	@echo   make              - buduje $(XEX_OUT) oraz weryfikuje mape pamieci
	@echo   make check_memory - generuje i weryfikuje docs/memory_map.txt i json
	@echo   make test         - uruchamia testy jednostkowe (pytest)
	@echo   make clean        - usuwa wygenerowane pliki ($(XEX_OUT), $(GEN_DIR)/)
	@echo   make run          - uruchamia $(XEX_OUT) w Altirra
	@echo   make help         - ta pomoc
