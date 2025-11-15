from .context import InteractiveContext
from .main import MainContext
from .logging import LoggingContext
from .hwmon import HWMONContext
from .main_loaded import LoadedContext
from .selected_fan import SelectedFanContext
from .hwmon_info import HwmonInfo

# Context structure:
#
# - main
#   - logging
#   - hwmon
#   - main_loaded
#     - fans_loaded
#