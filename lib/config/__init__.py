from .context import InteractiveContext
from .main import MainContext
from .logging import LoggingContext
from .hwmon import HWMONContext
from .main_loaded import MainLoadedContext
from .control import ControlFanContext
from .section import SectionContext

# Context structure:
#
# - main
#   - logging
#   - hwmon
#   - main_loaded
#     - section
#     - main_complete
#       - control