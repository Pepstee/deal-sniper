"""pytest configuration: make situation_monitor importable from projects/edge/."""
import pathlib
import sys

EDGE_DIR = pathlib.Path(__file__).parent.parent
FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"

# Ensure projects/edge/ is on the path so `import situation_monitor` resolves.
_edge_str = str(EDGE_DIR)
if _edge_str not in sys.path:
    sys.path.insert(0, _edge_str)
