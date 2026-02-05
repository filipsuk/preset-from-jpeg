from __future__ import annotations

import json
from pathlib import Path

import pytest

from lr_optim_api.config import (
    load_calibration,
    load_config,
    load_mappings,
    save_calibration,
    save_config,
    save_mappings,
)
from lr_optim_api.types import Calibration, ParamMapping, Rectangle


@pytest.fixture()
def tmp_config(tmp_path: Path) -> Path:
    return tmp_path / "config.json"


class TestConfigRoundtrip:
    def test_save_load_empty(self, tmp_config: Path) -> None:
        save_config({}, tmp_config)
        assert load_config(tmp_config) == {}

    def test_save_load_arbitrary(self, tmp_config: Path) -> None:
        data = {"foo": "bar", "num": 42}
        save_config(data, tmp_config)
        assert load_config(tmp_config) == data

    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        assert load_config(tmp_path / "nonexistent.json") == {}

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "config.json"
        save_config({"x": 1}, deep)
        assert deep.exists()


class TestCalibrationPersistence:
    def _make_cal(self) -> Calibration:
        return Calibration(
            window_id=99,
            window_width=2560,
            window_height=1440,
            reference_rect=Rectangle(x=10, y=100, width=600, height=400),
            current_rect=Rectangle(x=650, y=100, width=600, height=400),
        )

    def test_roundtrip(self, tmp_config: Path) -> None:
        cal = self._make_cal()
        save_calibration(cal, tmp_config)
        restored = load_calibration(tmp_config)
        assert restored is not None
        assert restored.window_id == 99
        assert restored.reference_rect == cal.reference_rect
        assert restored.current_rect == cal.current_rect

    def test_load_missing_returns_none(self, tmp_config: Path) -> None:
        assert load_calibration(tmp_config) is None

    def test_preserves_other_keys(self, tmp_config: Path) -> None:
        save_config({"other_key": "value"}, tmp_config)
        save_calibration(self._make_cal(), tmp_config)
        data = load_config(tmp_config)
        assert data["other_key"] == "value"
        assert "calibration" in data


class TestMappingsPersistence:
    def test_roundtrip(self, tmp_config: Path) -> None:
        mappings = {
            "TEMP": ParamMapping(mode="nrpn", control=0, lr_min=2000, lr_max=50000, lr_default=5500),
            "EXP": ParamMapping(mode="cc", control=7, lr_min=-5, lr_max=5),
        }
        save_mappings(mappings, tmp_config)
        restored = load_mappings(tmp_config)
        assert set(restored.keys()) == {"TEMP", "EXP"}
        assert restored["TEMP"].mode == "nrpn"
        assert restored["TEMP"].lr_min == 2000
        assert restored["EXP"].mode == "cc"

    def test_load_missing_returns_empty(self, tmp_config: Path) -> None:
        assert load_mappings(tmp_config) == {}
