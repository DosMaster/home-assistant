"""Common test utils for working with recorder."""

from datetime import timedelta

from homeassistant.components import recorder
from homeassistant.util import dt as dt_util

from tests.common import fire_time_changed


def wait_recording_done(hass):
    """Block till recording is done."""
    trigger_db_commit(hass)
    hass.block_till_done()
    hass.data[recorder.DATA_INSTANCE].block_till_done()
    hass.block_till_done()


def trigger_db_commit(hass):
    """Force the recorder to commit."""
    for _ in range(recorder.DEFAULT_COMMIT_INTERVAL):
        # We only commit on time change
        fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
