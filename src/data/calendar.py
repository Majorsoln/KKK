"""Kalenda ndogo ya siku za trading — kwa ajili ya ALERT ya DF-04 pekee.

TAHADHARI YA WIGO: kalenda KAMILI ya sessions inatengenezwa kutoka **data
yenyewe** kwenye T1 (spec §3: "Kalenda inatengenezwa kwa data yenyewe ... si
kudhaniwa"). Hii hapa ni kalenda ya chini kabisa inayohitajika ili recorder
ijue siku gani ukimya wake ni tatizo:

* Jumamosi — soko limefungwa;
* Jumapili — wiki inafunguka jioni (~22:00 UTC): ukimya wa siku nzima
  hauzalishi alert, lakini data ikipatikana inarekodiwa kama kawaida;
* Jumatatu–Ijumaa — siku kamili za trading: ukimya = ONYO (DF-04);
* sikukuu za `recorder.calendar.holidays_md` (mwezi-siku) zinatolewa.

Kila siku inayotolewa kwenye kalenda hii inarekodiwa kwenye ripoti ya freshness
ili PD aone kwamba ilitolewa kwa sheria, si kwa bahati mbaya.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

SATURDAY = 5
SUNDAY = 6
DEFAULT_HOLIDAYS_MD: tuple[str, ...] = ("01-01", "12-25")


@dataclass(frozen=True)
class TradingCalendar:
    """Kalenda ya muda ya siku za trading (itabadilishwa na kalenda ya data — T1)."""

    holidays_md: tuple[str, ...] = DEFAULT_HOLIDAYS_MD

    def is_holiday(self, day: date) -> bool:
        return day.strftime("%m-%d") in self.holidays_md

    def is_full_trading_day(self, day: date) -> bool:
        """Jumatatu–Ijumaa isiyo sikukuu — siku ambayo ukimya ni ONYO."""
        return day.weekday() < SATURDAY and not self.is_holiday(day)

    def is_trading_day(self, day: date) -> bool:
        """Siku yoyote inayoweza kuwa na ticks (pamoja na ufunguzi wa Jumapili)."""
        return day.weekday() != SATURDAY and not self.is_holiday(day)

    def full_trading_days(self, start: date, end: date) -> list[date]:
        """Siku kamili za trading kwenye [start, end] (pande zote mbili ndani)."""
        if end < start:
            return []
        days: list[date] = []
        cursor = start
        while cursor <= end:
            if self.is_full_trading_day(cursor):
                days.append(cursor)
            cursor += timedelta(days=1)
        return days

    def previous_full_trading_day(self, day: date) -> date:
        """Siku kamili ya trading iliyotangulia `day` (haijumuishi `day`)."""
        cursor = day - timedelta(days=1)
        for _ in range(30):
            if self.is_full_trading_day(cursor):
                return cursor
            cursor -= timedelta(days=1)
        raise ValueError(f"hakuna siku ya trading ndani ya siku 30 kabla ya {day}")


def calendar_from_config(cfg) -> TradingCalendar:
    """Kalenda kutoka `config/data.yaml` (`recorder.calendar.holidays_md`)."""
    holidays = cfg.get("recorder.calendar.holidays_md", list(DEFAULT_HOLIDAYS_MD))
    return TradingCalendar(holidays_md=tuple(str(h) for h in holidays))
