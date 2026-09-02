#!/usr/bin/env python3
"""Somme les cycles 6502/6507 entre deux WSYNC dans un listing DASM (-l).

Vérifie mécaniquement le budget de cycles (Protocole IA, backlog.md) plutôt que de se fier
au comptage manuel seul : lit les octets opcode réellement assemblés, additionne leur coût
en cycles via OPCODE_CYCLES, et compare au budget NTSC de 76 cycles/ligne ainsi qu'aux
annotations `; N cycles, position X` du source.

Limite connue : les segments doivent être en ligne droite (pas de branchement/saut) entre
deux WSYNC — c'est déjà la discipline imposée par convention 11.3 sur le chemin critique.
Les instructions marquées VARIABLE_CYCLE_OPCODES ont un coût de base qui peut varier
(franchissement de page, branchement pris) : le compte reporté est le minimum, à confirmer
manuellement si le budget est serré.

Bug corrigé le 2026-08-31 (découvert au Spike FRC) : DASM ajoute un espace après le dernier
octet listé sur les lignes à 3 octets (adressage absolu) avant la tabulation — l'ancienne
regex l'exigeait immédiatement, donc parse_lst() ignorait silencieusement toute instruction
LDA/STA absolue (aucune erreur, juste un total sous-compté). Les instructions zero-page/
immédiat (2 octets) n'étaient pas touchées, ce qui a masqué le bug jusqu'ici.
"""

import re
import sys
from dataclasses import dataclass, field

# (mnémonique, cycles de base). Coût officiel 6502, hors pénalité de franchissement de page
# et hors cycle supplémentaire de branchement pris (voir VARIABLE_CYCLE_OPCODES).
OPCODE_CYCLES = {
    0x00: ("BRK", 7), 0x01: ("ORA", 6), 0x05: ("ORA", 3), 0x06: ("ASL", 5),
    0x08: ("PHP", 3), 0x09: ("ORA", 2), 0x0A: ("ASL", 2), 0x0D: ("ORA", 4),
    0x0E: ("ASL", 6), 0x10: ("BPL", 2), 0x11: ("ORA", 5), 0x15: ("ORA", 4),
    0x16: ("ASL", 6), 0x18: ("CLC", 2), 0x19: ("ORA", 4), 0x1D: ("ORA", 4),
    0x1E: ("ASL", 7), 0x20: ("JSR", 6), 0x21: ("AND", 6), 0x24: ("BIT", 3),
    0x25: ("AND", 3), 0x26: ("ROL", 5), 0x28: ("PLP", 4), 0x29: ("AND", 2),
    0x2A: ("ROL", 2), 0x2C: ("BIT", 4), 0x2D: ("AND", 4), 0x2E: ("ROL", 6),
    0x30: ("BMI", 2), 0x31: ("AND", 5), 0x35: ("AND", 4), 0x36: ("ROL", 6),
    0x38: ("SEC", 2), 0x39: ("AND", 4), 0x3D: ("AND", 4), 0x3E: ("ROL", 7),
    0x40: ("RTI", 6), 0x41: ("EOR", 6), 0x45: ("EOR", 3), 0x46: ("LSR", 5),
    0x48: ("PHA", 3), 0x49: ("EOR", 2), 0x4A: ("LSR", 2), 0x4C: ("JMP", 3),
    0x4D: ("EOR", 4), 0x4E: ("LSR", 6), 0x50: ("BVC", 2), 0x51: ("EOR", 5),
    0x55: ("EOR", 4), 0x56: ("LSR", 6), 0x58: ("CLI", 2), 0x59: ("EOR", 4),
    0x5D: ("EOR", 4), 0x5E: ("LSR", 7), 0x60: ("RTS", 6), 0x61: ("ADC", 6),
    0x65: ("ADC", 3), 0x66: ("ROR", 5), 0x68: ("PLA", 4), 0x69: ("ADC", 2),
    0x6A: ("ROR", 2), 0x6C: ("JMP", 5), 0x6D: ("ADC", 4), 0x6E: ("ROR", 6),
    0x70: ("BVS", 2), 0x71: ("ADC", 5), 0x75: ("ADC", 4), 0x76: ("ROR", 6),
    0x78: ("SEI", 2), 0x79: ("ADC", 4), 0x7D: ("ADC", 4), 0x7E: ("ROR", 7),
    0x81: ("STA", 6), 0x84: ("STY", 3), 0x85: ("STA", 3), 0x86: ("STX", 3),
    0x88: ("DEY", 2), 0x8A: ("TXA", 2), 0x8C: ("STY", 4), 0x8D: ("STA", 4),
    0x8E: ("STX", 4), 0x90: ("BCC", 2), 0x91: ("STA", 6), 0x94: ("STY", 4),
    0x95: ("STA", 4), 0x96: ("STX", 4), 0x98: ("TYA", 2), 0x99: ("STA", 5),
    0x9A: ("TXS", 2), 0x9D: ("STA", 5), 0xA0: ("LDY", 2), 0xA1: ("LDA", 6),
    0xA2: ("LDX", 2), 0xA4: ("LDY", 3), 0xA5: ("LDA", 3), 0xA6: ("LDX", 3),
    0xA8: ("TAY", 2), 0xA9: ("LDA", 2), 0xAA: ("TAX", 2), 0xAC: ("LDY", 4),
    0xAD: ("LDA", 4), 0xAE: ("LDX", 4), 0xB0: ("BCS", 2), 0xB1: ("LDA", 5),
    0xB4: ("LDY", 4), 0xB5: ("LDA", 4), 0xB6: ("LDX", 4), 0xB8: ("CLV", 2),
    0xB9: ("LDA", 4), 0xBA: ("TSX", 2), 0xBC: ("LDY", 4), 0xBD: ("LDA", 4),
    0xBE: ("LDX", 4), 0xC0: ("CPY", 2), 0xC1: ("CMP", 6), 0xC4: ("CPY", 3),
    0xC5: ("CMP", 3), 0xC6: ("DEC", 5), 0xC8: ("INY", 2), 0xC9: ("CMP", 2),
    0xCA: ("DEX", 2), 0xCC: ("CPY", 4), 0xCD: ("CMP", 4), 0xCE: ("DEC", 6),
    0xD0: ("BNE", 2), 0xD1: ("CMP", 5), 0xD5: ("CMP", 4), 0xD6: ("DEC", 6),
    0xD8: ("CLD", 2), 0xD9: ("CMP", 4), 0xDD: ("CMP", 4), 0xDE: ("DEC", 7),
    0xE0: ("CPX", 2), 0xE1: ("SBC", 6), 0xE4: ("CPX", 3), 0xE5: ("SBC", 3),
    0xE6: ("INC", 5), 0xE8: ("INX", 2), 0xE9: ("SBC", 2), 0xEA: ("NOP", 2),
    0xEC: ("CPX", 4), 0xED: ("SBC", 4), 0xEE: ("INC", 6), 0xF0: ("BEQ", 2),
    0xF1: ("SBC", 5), 0xF5: ("SBC", 4), 0xF6: ("INC", 6), 0xF8: ("SED", 2),
    0xF9: ("SBC", 4), 0xFD: ("SBC", 4), 0xFE: ("INC", 7),
}

# Coût de base ci-dessus = minimum. Ces opcodes peuvent coûter plus cher (page franchie,
# branchement pris) — signalés dans le rapport plutôt que silencieusement ignorés.
VARIABLE_CYCLE_OPCODES = {
    0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0,  # branchements relatifs
    0x11, 0x19, 0x1D, 0x31, 0x39, 0x3D, 0x51, 0x59, 0x5D,
    0x71, 0x79, 0x7D, 0xB1, 0xB9, 0xBC, 0xBD, 0xBE,
    0xD1, 0xD9, 0xDD, 0xF1, 0xF9, 0xFD,
}

WSYNC_ADDRESS = 0x02
NTSC_CYCLES_PER_LINE = 76

LST_LINE = re.compile(
    r"^\s*\d+\s+([0-9a-fA-F]{4})\t+\s*((?:[0-9a-fA-F]{2}\s+)*[0-9a-fA-F]{2})\s*\t+\s*\S"
)
ANNOTATION = re.compile(r"(\d+)\s*cycles?,\s*position\s*(\d+)", re.IGNORECASE)


@dataclass
class Instruction:
    address: int
    opcode: int
    mnemonic: str
    cycles: int
    variable: bool
    comment: str
    line_no: int
    operand_address: int | None = None


def opcode_cycles(opcode: int) -> tuple[str, int, bool]:
    """Retourne (mnémonique inconnu si absent, cycles, coût_variable) pour un octet opcode."""
    if opcode not in OPCODE_CYCLES:
        raise ValueError(f"opcode inconnu: ${opcode:02X}")
    mnemonic, cycles = OPCODE_CYCLES[opcode]
    return mnemonic, cycles, opcode in VARIABLE_CYCLE_OPCODES


def parse_annotation(comment: str) -> tuple[int, int] | None:
    """Extrait (cycles_annoncés, position_annoncée) d'un commentaire `; N cycles, position X`."""
    m = ANNOTATION.search(comment)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_lst(lines: list[str]) -> list[Instruction]:
    instructions = []
    for line_no, raw in enumerate(lines, start=1):
        m = LST_LINE.match(raw)
        if not m:
            continue
        address = int(m.group(1), 16)
        byte_str = m.group(2).split()
        if not byte_str:
            continue
        opcode = int(byte_str[0], 16)
        if opcode not in OPCODE_CYCLES:
            continue
        mnemonic, cycles, variable = opcode_cycles(opcode)
        comment = raw.split(";", 1)[1] if ";" in raw else ""

        operand_address = None
        operand_bytes = [int(b, 16) for b in byte_str[1:]]
        if len(operand_bytes) == 1:
            operand_address = operand_bytes[0]
        elif len(operand_bytes) == 2:
            operand_address = operand_bytes[0] | (operand_bytes[1] << 8)

        instructions.append(
            Instruction(address, opcode, mnemonic, cycles, variable, comment, line_no, operand_address)
        )
    return instructions


def sum_segment(instructions: list[Instruction]) -> int:
    return sum(i.cycles for i in instructions)


def split_wsync_segments(instructions: list[Instruction]) -> list[list[Instruction]]:
    """Découpe en segments qui se terminent chacun par une écriture WSYNC (85/8D 02)."""
    segments: list[list[Instruction]] = []
    current: list[Instruction] = []
    for instr in instructions:
        current.append(instr)
        is_sta_wsync = (
            instr.mnemonic == "STA"
            and instr.opcode in (0x85, 0x8D)
            and instr.operand_address == WSYNC_ADDRESS
        )
        if is_sta_wsync:
            segments.append(current)
            current = []
    if current:
        segments.append(current)
    return segments


def report(lst_path: str) -> int:
    with open(lst_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    instructions = parse_lst(lines)
    segments = split_wsync_segments(instructions)

    exit_code = 0
    for seg_index, segment in enumerate(segments):
        total = sum_segment(segment)
        variable_flags = [i for i in segment if i.variable]
        margin = NTSC_CYCLES_PER_LINE - total
        status = "OK" if margin >= 0 else "DEPASSEMENT"
        if margin < 0:
            exit_code = 1

        print(f"--- Segment {seg_index + 1} (lignes source {segment[0].line_no}-{segment[-1].line_no}) ---")
        print(f"  cycles calculés : {total}  |  budget {NTSC_CYCLES_PER_LINE}  |  marge {margin}  |  {status}")
        if variable_flags:
            print(f"  ATTENTION : {len(variable_flags)} instruction(s) à coût variable (branchement/page) — "
                  f"compte ci-dessus = minimum, à confirmer manuellement")

        running = 0
        for instr in segment:
            annotation = parse_annotation(instr.comment)
            if annotation is not None:
                annotated_cycles, annotated_position = annotation
                if annotated_cycles != instr.cycles:
                    print(f"  MISMATCH ligne {instr.line_no}: annotation dit {annotated_cycles} cycles, "
                          f"opcode ${instr.opcode:02X} ({instr.mnemonic}) coûte {instr.cycles}")
                    exit_code = 1
                if annotated_position != running:
                    print(f"  MISMATCH ligne {instr.line_no}: annotation dit position {annotated_position}, "
                          f"calculé {running}")
                    exit_code = 1
            running += instr.cycles

    return exit_code


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <fichier.lst>", file=sys.stderr)
        return 2
    return report(argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
