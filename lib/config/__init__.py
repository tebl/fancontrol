from .context import InteractiveContext
from .main import MainContext
from .logging import LoggingContext
from .hwmon import HWMONContext
from .main_loaded import MainLoadedContext
from .section import SectionContext
from .main_complete import MainCompleteContext
from .fan_control import ControlFanContext

# Context structure:
#
# - main
#   - logging
#   - hwmon
#   - main_loaded
#     - section
#     - main_complete
#       - fan_control