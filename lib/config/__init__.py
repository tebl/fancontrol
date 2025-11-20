from .context import InteractiveContext
from .main import MainContext
from .logging import LoggingContext
from .hwmon import HWMONContext
from .main_loaded import MainLoadedContext
from .section import SectionContext
from .control_fan import ControlFanContext

# Context structure:
#
# - main
#   - logging
#   - hwmon
#   - main_loaded
#     - section
#     - main_complete
#       - control_fan