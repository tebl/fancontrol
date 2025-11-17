from .context import InteractiveContext
from .main import MainContext
from .logging import LoggingContext
from .hwmon import HWMONContext
from .main_loaded import LoadedContext
from .selected_fan import SelectedFanContext
from .section import SectionContext

# Context structure:
#
# - main
#   - logging
#   - hwmon
#   - main_loaded
#     - section
#       - section_tuning
#       - section_monitor
#     - fans_loaded
#