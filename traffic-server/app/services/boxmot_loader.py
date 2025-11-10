"""Helper to locate and expose the Boxmot (ByteTrack) tracker class across versions.

This centralises the dynamic import logic so other modules (e.g. realtime stream)
can simply `from app.services.boxmot_loader import BYTETracker, HAVE_BOXMOT`.
"""
import importlib
import logging
import traceback

logger = logging.getLogger(__name__)

# Candidate module paths and attribute/class names to try (ordered)
_CANDIDATES = [
    ("boxmot.tracker.byte_tracker", ["BYTETracker", "ByteTrack"]),
    ("boxmot.tracker.bytetrack", ["BYTETracker", "ByteTrack"]),
    ("boxmot.trackers.bytetrack.bytetrack", ["BYTETracker", "ByteTrack"]),
    ("boxmot.trackers.bytetrack", ["BYTETracker", "ByteTrack"]),
    ("boxmot.trackers.bytetrack.byte_tracker", ["BYTETracker", "ByteTrack"]),
]

BYTETracker = None
HAVE_BOXMOT = False

def _discover():
    global BYTETracker, HAVE_BOXMOT
    for module_name, attrs in _CANDIDATES:
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            continue

        for a in attrs:
            if hasattr(mod, a):
                BYTETracker = getattr(mod, a)
                HAVE_BOXMOT = True
                logger.info("✅ Found Boxmot tracker '%s' in module '%s'", a, module_name)
                return

    # not found
    HAVE_BOXMOT = False
    logger.warning("⚠️  Boxmot/ByteTrack not found in expected modules. See docs or run verify_boxmot.py")


# Run discovery on import
try:
    _discover()
except Exception:
    HAVE_BOXMOT = False
    logger.warning("Error while discovering boxmot tracker: %s", traceback.format_exc())


def instantiate_tracker(**kwargs):
    """Attempt to instantiate the discovered tracker class.

    Tries to call the tracker class with the provided kwargs; if that fails due
    to signature mismatch, falls back to no-arg construction.

    Returns the instance or raises the underlying exception.
    """
    if not HAVE_BOXMOT or BYTETracker is None:
        raise RuntimeError("Boxmot BYTETracker not available")

    try:
        return BYTETracker(**kwargs)
    except TypeError:
        # Fallback to no-arg constructor
        return BYTETracker()
