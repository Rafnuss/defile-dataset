"""The count site, and the sun there.

Défilé de l'Écluse (Ain/Haute-Savoie, France): a gorge of the Rhône between the Jura and the
Vuache, where migrating raptors funnel south-west. Counted from the same spot since 1966.
"""

import numpy as np
import pandas as pd
from suncalc import get_position

SITE_NAME = "Défilé de l'Écluse"
# Count point. defile-migration-forecast uses the same coordinates for its weather
# (`src/data/weather.py` LOCATIONS["Defile"]).
LATITUDE = 46.117215
LONGITUDE = 5.914877
COUNTRY_CODE = "FR"
TIMEZONE = "Europe/Paris"
TREKTELLEN_SITE_ID = 2422

# Sun altitude (degrees) below which it is night: the end of civil twilight. Also the night of
# defile-migration-forecast's model (`src/data/weather.py` NIGHT_SUN_ALTITUDE).
NIGHT_SUN_ALTITUDE = -6.0


def civil_twilight(local_dates, threshold_deg=NIGHT_SUN_ALTITUDE):
    """Dawn and dusk (UTC, to the minute) at the site for each local calendar date.

    Returns `(dawn, dusk)`, two Series indexed by the unique (naive, midnight) dates: the first
    minute of the day with the sun at or above `threshold_deg`, and the minute after the last.
    """
    dates = pd.DatetimeIndex(pd.Series(local_dates).dropna().unique()).normalize().unique()
    midnight = dates.tz_localize(TIMEZONE).tz_convert("UTC")
    minutes = np.arange(24 * 60).astype("timedelta64[m]")
    grid = pd.DatetimeIndex((midnight.values[:, None] + minutes[None, :]).ravel())
    altitude = np.degrees(np.asarray(get_position(grid, LONGITUDE, LATITUDE)["altitude"]))
    day = altitude.reshape(len(dates), -1) >= threshold_deg
    first = day.argmax(axis=1)
    last = day.shape[1] - 1 - day[:, ::-1].argmax(axis=1)
    dawn = pd.Series(midnight + pd.to_timedelta(first, unit="min"), index=dates)
    dusk = pd.Series(midnight + pd.to_timedelta(last + 1, unit="min"), index=dates)
    return dawn, dusk
