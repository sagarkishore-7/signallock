"""SignalLock attack/defense showcase — OPTIONAL, LOCALHOST-ONLY, NON-LOAD-BEARING.

This package demonstrates the core thesis end to end: a weak, OSINT-derived
password ("rex2014") is cracked by a targeted-guess attacker driven by
``signallock.predict.mangling``, and then — after hardening — the same attack
fails within budget.

Safety boundaries:

- The demo target is a *local* in-memory FastAPI auth service. It NEVER attacks
  live third-party hosts. ``run_attack`` refuses any non-loopback URL via
  :func:`demo.run_attack.assert_loopback`.
- It is not imported by the SignalLock library, API, or CLI and carries no
  product behavior. Treat it as a runnable explainer only.
"""
