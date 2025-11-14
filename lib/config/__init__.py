from .context import InteractiveContext
from .main import MainContext
from .logging import LoggingContext
from .hwmon import HwMonContext
from .main_loaded import LoadedContext
from .fans import FanContext

# Context structure:
#
# - main
#   - logging
#   - hwmon
#   - main_loaded
#     - fans
#