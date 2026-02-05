from __future__ import annotations

import pytest

from lr_optim_api.types import Calibration, ParamMapping, Rectangle, WindowInfo


class TestRectangle:
    def test_pil_box(self) -> None:
        r = Rectangle(x=10, y=20, width=100, height=50)
        assert r.pil_box == (10, 20, 110, 70)

    def test_right_bottom(self) -> None:
        r = Rectangle(x=5, y=15, width=200, height=300)
        assert r.right == 205
        assert r.bottom == 315

    def test_roundtrip_dict(self) -> None:
        original = Rectangle(x=0, y=0, width=1920, height=1080)
        restored = Rectangle.from_dict(original.to_dict())
        assert restored == original

    def test_frozen(self) -> None:
        r = Rectangle(x=0, y=0, width=10, height=10)
        with pytest.raises(AttributeError):
            r.x = 5  # type: ignore[misc]


class TestCalibration:
    def test_roundtrip_dict(self) -> None:
        cal = Calibration(
            window_id=42,
            window_width=2560,
            window_height=1440,
            reference_rect=Rectangle(x=10, y=100, width=600, height=400),
            current_rect=Rectangle(x=650, y=100, width=600, height=400),
        )
        restored = Calibration.from_dict(cal.to_dict())
        assert restored.window_id == cal.window_id
        assert restored.reference_rect == cal.reference_rect
        assert restored.current_rect == cal.current_rect

    def test_to_dict_structure(self) -> None:
        cal = Calibration(
            window_id=1,
            window_width=800,
            window_height=600,
            reference_rect=Rectangle(x=0, y=0, width=100, height=100),
            current_rect=Rectangle(x=200, y=0, width=100, height=100),
        )
        d = cal.to_dict()
        assert set(d.keys()) == {
            "window_id",
            "window_width",
            "window_height",
            "reference_rect",
            "current_rect",
        }
        assert isinstance(d["reference_rect"], dict)


class TestParamMapping:
    def test_norm_to_midi_cc(self) -> None:
        m = ParamMapping(mode="cc", control=1, lr_min=-100, lr_max=100)
        assert m.norm_to_midi(0.0) == 0
        assert m.norm_to_midi(1.0) == 127
        assert m.norm_to_midi(0.5) == 64

    def test_norm_to_midi_nrpn(self) -> None:
        m = ParamMapping(mode="nrpn", control=200, lr_min=-5, lr_max=5)
        assert m.norm_to_midi(0.0) == 0
        assert m.norm_to_midi(1.0) == 16383
        assert m.norm_to_midi(0.5) == 8192

    def test_norm_to_midi_clamps(self) -> None:
        m = ParamMapping(mode="cc", control=1, lr_min=0, lr_max=100)
        assert m.norm_to_midi(-0.5) == 0
        assert m.norm_to_midi(1.5) == 127

    def test_lr_to_norm(self) -> None:
        m = ParamMapping(mode="nrpn", control=0, lr_min=-100, lr_max=100)
        assert m.lr_to_norm(-100) == pytest.approx(0.0)
        assert m.lr_to_norm(0) == pytest.approx(0.5)
        assert m.lr_to_norm(100) == pytest.approx(1.0)

    def test_lr_to_norm_asymmetric(self) -> None:
        m = ParamMapping(mode="nrpn", control=0, lr_min=2000, lr_max=50000)
        assert m.lr_to_norm(2000) == pytest.approx(0.0)
        assert m.lr_to_norm(50000) == pytest.approx(1.0)
        assert m.lr_to_norm(26000) == pytest.approx(0.5)

    def test_midi_max(self) -> None:
        assert ParamMapping(mode="cc", control=1, lr_min=0, lr_max=1).midi_max == 127
        assert ParamMapping(mode="nrpn", control=1, lr_min=0, lr_max=1).midi_max == 16383
