"""Kutekeleza vikapu — DOCTRINE §4.1, §5, R12.

RCE ni mamlaka ya gharama, ukubwa na ruhusa. Kazi hapa ni kuchukua bei sahihi
za utekelezaji, kuepuka kuhesabu gharama mara mbili, na kutoa hesabu katika
vipimo vya R.
"""

from .runner import (  # noqa: F401
    PARTIAL_EXECUTION,
    Execution,
    ExecuteError,
    Trade,
    execute,
    execute_all,
)
