"""Sensor modules for Monica - the security monitoring agent.

Each sensor exposes a single callable `collect` that accepts a `context`
dictionary and returns a payload describing the current state of that
sensor.  Sensors should not perform long blocking operations; they will
be executed by the scheduler at a configured interval.

To add a new sensor simply create a new module within this package that
implements a `collect(context) -> dict` function.
"""
