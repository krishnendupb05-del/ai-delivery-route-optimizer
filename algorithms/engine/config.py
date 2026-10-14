"""Operating constants for converting distance to time. Single source for defaults.

Time convention: all times are minutes since midnight (0-1440). 10:00 = 600.
"""

MINUTES_PER_DAY = 1440

# Average urban delivery speed, used to convert km to travel minutes.
DEFAULT_SPEED_KMH = 30.0

# Fixed time spent unloading at each stop.
DEFAULT_SERVICE_TIME_MIN = 5.0

# Time spent reloading at the depot on each mid-route return trip
# (not added for the final return at the end of the route).
DEFAULT_RELOAD_TIME_MIN = 10.0

# Default dispatch time: 09:00.
DEFAULT_DISPATCH_TIME_MIN = 540
