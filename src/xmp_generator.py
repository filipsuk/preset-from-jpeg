"""
xmp_generator.py - Generate Lightroom Classic .xmp preset files.

Creates valid XMP files that can be imported into Lightroom Classic 14.5+.
"""

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)


XMP_TEMPLATE = '''<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
    crs:PresetType="Normal"
    crs:Cluster=""
    crs:UUID="{uuid}"
    crs:SupportsAmount="False"
    crs:SupportsColor="True"
    crs:SupportsMonochrome="True"
    crs:SupportsHighDynamicRange="True"
    crs:SupportsNormalDynamicRange="True"
    crs:SupportsSceneReferred="True"
    crs:SupportsOutputReferred="True"
    crs:CameraModelRestriction=""
    crs:Copyright=""
    crs:ContactInfo=""
    crs:Version="15.4"
    crs:ProcessVersion="15.4"
    crs:ConvertToGrayscale="False"
    crs:CameraProfile="Adobe Standard"
{parameters}   >
{tone_curves}  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''


class XMPGenerator:
    """
    Generates Lightroom Classic .xmp preset files.
    """

    def __init__(self, preset_name: str = "ColorScienceEmulator"):
        """
        Initialize XMP generator.

        Args:
            preset_name: Name for the preset
        """
        self.preset_name = preset_name

    def generate(
        self,
        params: Dict[str, Any],
        output_path: Union[str, Path],
    ) -> str:
        """
        Generate a Lightroom .xmp preset file.

        Args:
            params: Optimized parameters dictionary
            output_path: Path to save the .xmp file

        Returns:
            Path to generated XMP file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate UUID
        preset_uuid = str(uuid.uuid4()).upper()

        # Format simple parameters
        param_lines = []
        for key, value in params.items():
            if key.startswith("ToneCurve"):
                continue  # Handle curves separately
            formatted = self._format_param(key, value)
            if formatted:
                param_lines.append(f"    crs:{formatted}")

        # Format tone curves
        curve_sections = []
        for curve_name in [
            "ToneCurvePV2012",
            "ToneCurvePV2012Red",
            "ToneCurvePV2012Green",
            "ToneCurvePV2012Blue",
        ]:
            if curve_name in params and params[curve_name]:
                curve_xml = self._format_tone_curve(curve_name, params[curve_name])
                curve_sections.append(curve_xml)

        # Assemble XMP
        xmp_content = XMP_TEMPLATE.format(
            uuid=preset_uuid,
            parameters="\n".join(param_lines) + "\n" if param_lines else "",
            tone_curves="\n".join(curve_sections) + "\n" if curve_sections else "",
        )

        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xmp_content)

        logger.info(f"Generated XMP preset: {output_path}")
        return str(output_path)

    def _format_param(self, key: str, value: Any) -> str:
        """
        Format a parameter for XMP.

        Args:
            key: Parameter name
            value: Parameter value

        Returns:
            Formatted parameter string or None
        """
        if value is None:
            return None

        if isinstance(value, bool):
            return f'{key}="{str(value)}"'
        elif isinstance(value, float):
            # Round to integer for most Lightroom parameters
            int_value = int(round(value))
            if int_value == 0:
                return f'{key}="0"'
            return f'{key}="{int_value:+d}"'
        elif isinstance(value, int):
            if value == 0:
                return f'{key}="0"'
            return f'{key}="{value:+d}"'
        elif isinstance(value, str):
            return f'{key}="{value}"'

        return None

    def _format_tone_curve(
        self,
        curve_name: str,
        points: List[Tuple[float, float]],
    ) -> str:
        """
        Format a tone curve for XMP.

        Args:
            curve_name: Curve parameter name
            points: List of (input, output) points normalized 0-1

        Returns:
            XML string for the curve
        """
        # Convert points from 0-1 to 0-255 scale
        scaled_points = []
        for inp, out in points:
            scaled_in = int(round(inp * 255))
            scaled_out = int(round(out * 255))
            scaled_points.append(f"{scaled_in}, {scaled_out}")

        point_str = ", ".join(scaled_points)

        return f'''   <crs:{curve_name}>
    <rdf:Seq>
     <rdf:li>{point_str}</rdf:li>
    </rdf:Seq>
   </crs:{curve_name}>'''

    def validate_xmp(self, xmp_path: Union[str, Path]) -> bool:
        """
        Validate that an XMP file is well-formed XML.

        Args:
            xmp_path: Path to XMP file

        Returns:
            True if valid, False otherwise
        """
        import xml.etree.ElementTree as ET

        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()
            return root is not None
        except ET.ParseError as e:
            logger.error(f"XMP validation failed: {e}")
            return False
        except FileNotFoundError:
            logger.error(f"XMP file not found: {xmp_path}")
            return False


def create_minimal_xmp(output_path: Union[str, Path]) -> str:
    """
    Create a minimal valid XMP preset file.

    Useful for testing XMP import.

    Args:
        output_path: Path to save the file

    Returns:
        Path to generated file
    """
    gen = XMPGenerator()
    params = {
        "HueAdjustmentRed": 0,
        "SaturationAdjustmentRed": 0,
    }
    return gen.generate(params, output_path)


def params_to_xmp_string(params: Dict[str, Any]) -> str:
    """
    Convert parameters to XMP content string without saving to file.

    Args:
        params: Parameter dictionary

    Returns:
        XMP content as string
    """
    gen = XMPGenerator()
    preset_uuid = str(uuid.uuid4()).upper()

    param_lines = []
    for key, value in params.items():
        if key.startswith("ToneCurve"):
            continue
        formatted = gen._format_param(key, value)
        if formatted:
            param_lines.append(f"    crs:{formatted}")

    curve_sections = []
    for curve_name in [
        "ToneCurvePV2012",
        "ToneCurvePV2012Red",
        "ToneCurvePV2012Green",
        "ToneCurvePV2012Blue",
    ]:
        if curve_name in params and params[curve_name]:
            curve_xml = gen._format_tone_curve(curve_name, params[curve_name])
            curve_sections.append(curve_xml)

    return XMP_TEMPLATE.format(
        uuid=preset_uuid,
        parameters="\n".join(param_lines) + "\n" if param_lines else "",
        tone_curves="\n".join(curve_sections) + "\n" if curve_sections else "",
    )
