"""Uchambuzi wa matokeo — DOCTRINE §7.2.

Kitengo cha uchambuzi ni **siku ya portfolio**, si trade. Trades za siku moja
zinajumlishwa kuwa nambari moja, kwa hiyo legs sita za F1 ni uchunguzi mmoja.
`p-value` inatoka kwenye block bootstrap, si t-test.
"""

from .bootstrap import (  # noqa: F401
    B_CERTIFICATION,
    B_DEVELOPMENT,
    MAX_BLOCK_FRACTION,
    MIN_BLOCK_DAYS,
    BootstrapError,
    BootstrapResult,
    optimal_block_length,
    test_mean_positive,
)
from .curve import Curve, CurveError, combine, daily_r  # noqa: F401
