import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from cycle_linter import (  # noqa: E402
    Instruction,
    opcode_cycles,
    parse_annotation,
    parse_lst,
    split_wsync_segments,
    sum_segment,
)


def test_opcode_cycles_known_store():
    mnemonic, cycles, variable = opcode_cycles(0x85)  # STA zero-page
    assert mnemonic == "STA"
    assert cycles == 3
    assert variable is False


def test_opcode_cycles_variable_branch():
    _, cycles, variable = opcode_cycles(0xD0)  # BNE
    assert cycles == 2
    assert variable is True


def test_opcode_cycles_unknown_raises():
    try:
        opcode_cycles(0x02)  # non défini dans la table (illégal / non utilisé ici)
        assert False, "devrait lever ValueError"
    except ValueError:
        pass


def test_parse_annotation_extracts_cycles_and_position():
    comment = " 3 cycles, position 14, doit finir @14-17 (bus-stuffed)"
    assert parse_annotation(comment) == (3, 14)


def test_parse_annotation_none_when_absent():
    assert parse_annotation(" pas d'annotation ici") is None


def test_sum_segment_adds_instruction_cycles():
    instructions = [
        Instruction(0xF000, 0xA9, "LDA", 2, False, "", 1),
        Instruction(0xF002, 0x85, "STA", 3, False, "", 2),
        Instruction(0xF004, 0x85, "STA", 3, False, "", 3),
    ]
    assert sum_segment(instructions) == 8


def test_split_wsync_segments_splits_only_on_real_wsync_writes():
    instructions = [
        Instruction(0xF000, 0x85, "STA", 3, False, "", 1, operand_address=0x0D),  # STA PF0
        Instruction(0xF002, 0x85, "STA", 3, False, "", 2, operand_address=0x02),  # STA WSYNC
        Instruction(0xF004, 0x85, "STA", 3, False, "", 3, operand_address=0x1B),  # STA GRP0
    ]
    segments = split_wsync_segments(instructions)
    assert len(segments) == 2
    assert len(segments[0]) == 2
    assert len(segments[1]) == 1


def test_parse_lst_reads_absolute_addressing_line():
    # Format DASM réel pour une instruction 3 octets (ex. STA absolu) : un espace de
    # plus après le dernier octet, avant la tabulation, que sur une ligne 2 octets.
    # Régression pour le bug corrigé le 2026-08-31 (Spike FRC) : ces lignes étaient
    # ignorées silencieusement par parse_lst(), sous-comptant tout segment qui en contenait.
    line = "     80  f034\t\t       8d 41 f0 \t      sta\tReadColor+2\t; 4 cycles, position 14\n"
    instructions = parse_lst([line])
    assert len(instructions) == 1
    assert instructions[0].mnemonic == "STA"
    assert instructions[0].cycles == 4
    assert instructions[0].operand_address == 0xF041


def test_parse_lst_reads_generated_listing():
    lst_path = Path(__file__).resolve().parents[1] / "spikes" / "spike_0_1" / "spike_0_1.lst"
    if not lst_path.exists():
        import pytest
        pytest.skip("spike_0_1.lst pas encore assemblé (dasm requis)")

    instructions = parse_lst(lst_path.read_text().splitlines())
    assert len(instructions) > 0
    segments = split_wsync_segments(instructions)
    totals = [sum_segment(seg) for seg in segments]
    assert all(t <= 76 for t in totals), "aucun segment ne doit dépasser le budget NTSC de 76 cycles/ligne"
