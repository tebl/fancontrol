from .context import InteractiveContext
from .main import MainContext
from .logging import LoggingContext
from .hwmon import HWMONContext
from .main_loaded import LoadedContext
from .selected_fan import SelectedFanContext
from .section import SectionContext
from .section_pwm_input import SectionPWMInputContext

# Context structure:
#
# - main
#   - logging
#   - hwmon
#   - main_loaded
#     - section
#       - section_pwm_input
#     - fans_loaded
#