"""Music and sound-effect playback.

The pygame support prompt is hidden here, before ``manager`` imports
pygame, so the import can stay at the top of that module.
"""

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
