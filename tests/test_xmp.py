"""
test_xmp.py - Unit tests for the XMP generator module.
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.xmp_generator import XMPGenerator, create_minimal_xmp, params_to_xmp_string


class TestXMPGenerator:
    """Tests for the XMPGenerator class."""

    def test_generates_valid_xml(self):
        """Generated XMP should be valid XML."""
        gen = XMPGenerator()
        params = {"HueAdjustmentRed": 10, "SaturationAdjustmentBlue": -5}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            # Parse XML - should not raise
            tree = ET.parse(output_path)
            root = tree.getroot()
            assert root is not None
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_validates_generated_xmp(self):
        """Validation should pass for generated XMP."""
        gen = XMPGenerator()
        params = {"HueAdjustmentRed": 10}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)
            assert gen.validate_xmp(output_path) is True
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_contains_required_namespaces(self):
        """XMP should contain required namespaces."""
        gen = XMPGenerator()
        params = {}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert "xmlns:crs" in content
            assert "xmlns:rdf" in content
            assert "http://ns.adobe.com/camera-raw-settings/1.0/" in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_contains_process_version(self):
        """XMP should contain ProcessVersion."""
        gen = XMPGenerator()
        params = {}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert "ProcessVersion" in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_contains_camera_profile(self):
        """XMP should contain CameraProfile."""
        gen = XMPGenerator()
        params = {}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert "CameraProfile" in content
            assert "Adobe Standard" in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_contains_uuid(self):
        """XMP should contain a UUID."""
        gen = XMPGenerator()
        params = {}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert "crs:UUID" in content
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestToneCurveFormatting:
    """Tests for tone curve formatting."""

    def test_formats_tone_curve(self):
        """Tone curves should be formatted correctly."""
        gen = XMPGenerator()
        params = {
            "ToneCurvePV2012": [(0, 0), (0.5, 0.5), (1, 1)],
        }

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert "ToneCurvePV2012" in content
            assert "rdf:Seq" in content
            assert "rdf:li" in content
            # Check for scaled values (0-255 range)
            assert "0, 0" in content
            assert "255, 255" in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_formats_rgb_curves(self):
        """RGB curves should be included."""
        gen = XMPGenerator()
        params = {
            "ToneCurvePV2012Red": [(0, 0), (1, 1)],
            "ToneCurvePV2012Green": [(0, 0), (1, 1)],
            "ToneCurvePV2012Blue": [(0, 0), (1, 1)],
        }

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert "ToneCurvePV2012Red" in content
            assert "ToneCurvePV2012Green" in content
            assert "ToneCurvePV2012Blue" in content
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestParameterFormatting:
    """Tests for parameter formatting."""

    def test_formats_positive_integer(self):
        """Positive integers should have + sign."""
        gen = XMPGenerator()
        params = {"HueAdjustmentRed": 10}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert 'HueAdjustmentRed="+10"' in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_formats_negative_integer(self):
        """Negative integers should have - sign."""
        gen = XMPGenerator()
        params = {"HueAdjustmentRed": -10}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert 'HueAdjustmentRed="-10"' in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_formats_zero(self):
        """Zero should be formatted without sign."""
        gen = XMPGenerator()
        params = {"HueAdjustmentRed": 0}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert 'HueAdjustmentRed="0"' in content
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_rounds_floats(self):
        """Float values should be rounded to integers."""
        gen = XMPGenerator()
        params = {"HueAdjustmentRed": 10.7}

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            gen.generate(params, output_path)

            with open(output_path, "r") as f:
                content = f.read()

            assert 'HueAdjustmentRed="+11"' in content
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_create_minimal_xmp(self):
        """Minimal XMP should be valid."""
        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False) as f:
            output_path = f.name

        try:
            create_minimal_xmp(output_path)

            # Should parse without error
            tree = ET.parse(output_path)
            assert tree.getroot() is not None
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_params_to_xmp_string(self):
        """String generation should produce valid XMP."""
        params = {"HueAdjustmentRed": 5}
        content = params_to_xmp_string(params)

        assert "<?xpacket" in content
        assert "HueAdjustmentRed" in content
        assert "</x:xmpmeta>" in content


class TestValidation:
    """Tests for XMP validation."""

    def test_invalid_xml_fails_validation(self):
        """Invalid XML should fail validation."""
        gen = XMPGenerator()

        with tempfile.NamedTemporaryFile(suffix=".xmp", delete=False, mode="w") as f:
            f.write("not valid xml")
            output_path = f.name

        try:
            assert gen.validate_xmp(output_path) is False
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_missing_file_fails_validation(self):
        """Missing file should fail validation."""
        gen = XMPGenerator()
        # This file doesn't exist
        assert gen.validate_xmp("/nonexistent/path.xmp") is False
