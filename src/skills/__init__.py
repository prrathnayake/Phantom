"""Skills are higher level behaviours built on top of sensors and analysis.

Each skill defines a `run` function that is invoked by the scheduler.
Skills may use the context, storage, and the OpenRouter client to
perform more advanced tasks such as summarising anomalies or checking
for vulnerabilities.  Adding new skills follows the same pattern.
"""
