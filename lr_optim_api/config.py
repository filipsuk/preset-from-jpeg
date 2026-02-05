"""Persist and load calibration / MIDI mapping configuration."""

from __future__ import annotations

import json
from pathlib import Path

from .types import Calibration, ParamMapping

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "lr_optim_api"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict:
    path = Path(path).expanduser()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(data: dict, path: Path | str = DEFAULT_CONFIG_PATH) -> Path:
    path = Path(path).expanduser()
    _ensure_dir(path)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def load_calibration(path: Path | str = DEFAULT_CONFIG_PATH) -> Calibration | None:
    data = load_config(path)
    cal_data = data.get("calibration")
    if cal_data is None:
        return None
    return Calibration.from_dict(cal_data)


def save_calibration(
    calibration: Calibration, path: Path | str = DEFAULT_CONFIG_PATH
) -> Path:
    data = load_config(path)
    data["calibration"] = calibration.to_dict()
    return save_config(data, path)


def load_mappings(
    path: Path | str = DEFAULT_CONFIG_PATH,
) -> dict[str, ParamMapping]:
    data = load_config(path)
    raw = data.get("midi_mappings", {})
    return {
        key: ParamMapping(
            mode=v["mode"],
            control=v["control"],
            lr_min=v["lr_min"],
            lr_max=v["lr_max"],
            lr_default=v.get("lr_default", 0),
        )
        for key, v in raw.items()
    }


def save_mappings(
    mappings: dict[str, ParamMapping],
    path: Path | str = DEFAULT_CONFIG_PATH,
) -> Path:
    data = load_config(path)
    raw: dict[str, dict] = {}
    for key, m in mappings.items():
        raw[key] = {
            "mode": m.mode,
            "control": m.control,
            "lr_min": m.lr_min,
            "lr_max": m.lr_max,
            "lr_default": m.lr_default,
        }
    data["midi_mappings"] = raw
    return save_config(data, path)
