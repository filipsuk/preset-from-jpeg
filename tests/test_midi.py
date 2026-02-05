from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from xml.etree.ElementTree import fromstring

from lr_optim_api.midi2lr import (
    DEFAULT_MAPPINGS,
    generate_midi2lr_profile,
    send_cc,
    send_nrpn,
    set_param,
)
from lr_optim_api.types import ParamMapping


@pytest.fixture()
def mock_port() -> MagicMock:
    return MagicMock()


class TestSendCC:
    def test_sends_one_message(self, mock_port: MagicMock) -> None:
        send_cc(mock_port, channel=0, control=7, value_0_127=100)
        assert mock_port.send.call_count == 1

    def test_clamps_high(self, mock_port: MagicMock) -> None:
        send_cc(mock_port, channel=0, control=1, value_0_127=200)
        msg = mock_port.send.call_args[0][0]
        assert msg.value == 127

    def test_clamps_low(self, mock_port: MagicMock) -> None:
        send_cc(mock_port, channel=0, control=1, value_0_127=-5)
        msg = mock_port.send.call_args[0][0]
        assert msg.value == 0

    def test_channel_propagated(self, mock_port: MagicMock) -> None:
        send_cc(mock_port, channel=3, control=10, value_0_127=64)
        msg = mock_port.send.call_args[0][0]
        assert msg.channel == 3


class TestSendNRPN:
    def test_sends_four_messages(self, mock_port: MagicMock) -> None:
        send_nrpn(mock_port, channel=0, nrpn_number=500, value_0_16383=8192)
        assert mock_port.send.call_count == 4

    def test_cc_numbers_are_99_98_6_38(self, mock_port: MagicMock) -> None:
        send_nrpn(mock_port, channel=0, nrpn_number=0, value_0_16383=0)
        cc_numbers = [c[0][0].control for c in mock_port.send.call_args_list]
        assert cc_numbers == [99, 98, 6, 38]

    def test_nrpn_number_split(self, mock_port: MagicMock) -> None:
        send_nrpn(mock_port, channel=0, nrpn_number=300, value_0_16383=0)
        calls = mock_port.send.call_args_list
        nrpn_msb = calls[0][0][0].value
        nrpn_lsb = calls[1][0][0].value
        assert (nrpn_msb << 7) | nrpn_lsb == 300

    def test_value_split(self, mock_port: MagicMock) -> None:
        send_nrpn(mock_port, channel=0, nrpn_number=0, value_0_16383=10000)
        calls = mock_port.send.call_args_list
        val_msb = calls[2][0][0].value
        val_lsb = calls[3][0][0].value
        assert (val_msb << 7) | val_lsb == 10000

    def test_clamps_value(self, mock_port: MagicMock) -> None:
        send_nrpn(mock_port, channel=0, nrpn_number=0, value_0_16383=99999)
        calls = mock_port.send.call_args_list
        val_msb = calls[2][0][0].value
        val_lsb = calls[3][0][0].value
        assert (val_msb << 7) | val_lsb == 16383

    def test_zero_value(self, mock_port: MagicMock) -> None:
        send_nrpn(mock_port, channel=0, nrpn_number=0, value_0_16383=0)
        calls = mock_port.send.call_args_list
        val_msb = calls[2][0][0].value
        val_lsb = calls[3][0][0].value
        assert val_msb == 0
        assert val_lsb == 0

    def test_max_value(self, mock_port: MagicMock) -> None:
        send_nrpn(mock_port, channel=0, nrpn_number=0, value_0_16383=16383)
        calls = mock_port.send.call_args_list
        val_msb = calls[2][0][0].value
        val_lsb = calls[3][0][0].value
        assert (val_msb << 7) | val_lsb == 16383


class TestSetParam:
    def test_dispatches_nrpn(self, mock_port: MagicMock) -> None:
        m = ParamMapping(mode="nrpn", control=42, lr_min=0, lr_max=100)
        set_param(mock_port, channel=0, mapping=m, value_norm=0.5)
        assert mock_port.send.call_count == 4

    def test_dispatches_cc(self, mock_port: MagicMock) -> None:
        m = ParamMapping(mode="cc", control=7, lr_min=0, lr_max=100)
        set_param(mock_port, channel=0, mapping=m, value_norm=0.5)
        assert mock_port.send.call_count == 1

    def test_norm_zero_sends_midi_zero(self, mock_port: MagicMock) -> None:
        m = ParamMapping(mode="cc", control=7, lr_min=-100, lr_max=100)
        set_param(mock_port, channel=0, mapping=m, value_norm=0.0)
        msg = mock_port.send.call_args[0][0]
        assert msg.value == 0


class TestDefaultMappings:
    def test_all_entries_are_param_mappings(self) -> None:
        for key, val in DEFAULT_MAPPINGS.items():
            assert isinstance(val, ParamMapping), f"{key} is not a ParamMapping"

    def test_exposure_range(self) -> None:
        m = DEFAULT_MAPPINGS["EXPOSURE"]
        assert m.lr_min == -5
        assert m.lr_max == 5

    def test_hsl_keys_present(self) -> None:
        expected_prefixes = ["HSL_RED", "HSL_ORANGE", "HSL_YELLOW", "HSL_GREEN",
                             "HSL_AQUA", "HSL_BLUE", "HSL_PURPLE", "HSL_MAGENTA"]
        for prefix in expected_prefixes:
            for suffix in ["_HUE", "_SAT", "_LUM"]:
                assert f"{prefix}{suffix}" in DEFAULT_MAPPINGS

    def test_nrpn_numbers_start_at_128(self) -> None:
        for key, m in DEFAULT_MAPPINGS.items():
            assert m.control >= 128, f"{key} has control={m.control}, must be >= 128"

    def test_nrpn_numbers_unique(self) -> None:
        controls = [m.control for m in DEFAULT_MAPPINGS.values()]
        assert len(controls) == len(set(controls))

    def test_all_entries_have_lr_command(self) -> None:
        for key, m in DEFAULT_MAPPINGS.items():
            assert m.lr_command, f"{key} missing lr_command"

    def test_lr_commands_unique(self) -> None:
        commands = [m.lr_command for m in DEFAULT_MAPPINGS.values()]
        assert len(commands) == len(set(commands))


class TestGenerateProfile:
    def test_returns_element_tree(self) -> None:
        tree = generate_midi2lr_profile()
        root = tree.getroot()
        assert root.tag == "settings"

    def test_produces_one_setting_per_mapping(self) -> None:
        tree = generate_midi2lr_profile()
        settings = tree.getroot().findall("setting")
        assert len(settings) == len(DEFAULT_MAPPINGS)

    def test_setting_attributes(self) -> None:
        tree = generate_midi2lr_profile()
        first = tree.getroot().find("setting")
        assert first is not None
        assert set(first.attrib.keys()) == {"channel", "controller", "command_string"}

    def test_channel_default_is_1(self) -> None:
        tree = generate_midi2lr_profile()
        for setting in tree.getroot().findall("setting"):
            assert setting.get("channel") == "1"

    def test_custom_channel(self) -> None:
        tree = generate_midi2lr_profile(channel=5)
        for setting in tree.getroot().findall("setting"):
            assert setting.get("channel") == "5"

    def test_controller_matches_nrpn_number(self) -> None:
        tree = generate_midi2lr_profile()
        settings = tree.getroot().findall("setting")
        expected_controls = [str(m.control) for m in DEFAULT_MAPPINGS.values()]
        actual_controls = [s.get("controller") for s in settings]
        assert actual_controls == expected_controls

    def test_command_string_matches_lr_command(self) -> None:
        tree = generate_midi2lr_profile()
        settings = tree.getroot().findall("setting")
        expected_commands = [m.lr_command for m in DEFAULT_MAPPINGS.values()]
        actual_commands = [s.get("command_string") for s in settings]
        assert actual_commands == expected_commands

    def test_skips_empty_lr_command(self) -> None:
        mappings = {
            "A": ParamMapping(mode="nrpn", control=200, lr_min=0, lr_max=100, lr_command="Foo"),
            "B": ParamMapping(mode="nrpn", control=201, lr_min=0, lr_max=100, lr_command=""),
        }
        tree = generate_midi2lr_profile(mappings)
        settings = tree.getroot().findall("setting")
        assert len(settings) == 1
        assert settings[0].get("command_string") == "Foo"

    def test_xml_is_well_formed(self, tmp_path) -> None:
        tree = generate_midi2lr_profile()
        path = tmp_path / "test_profile.xml"
        tree.write(path, encoding="unicode", xml_declaration=True)
        xml_text = path.read_text()
        fromstring(xml_text)
