# ELITEFX

Repo hii ina vitu viwili pekee: **RCE** (code inayofanya kazi) na **DOCTRINE** (kile
kinachojengwa baadaye).

```
├── docs/RISK_COST_ENGINE.md    spec ya RCE — HAIGUSWI
├── docs/DOCTRINE.md            injini ya kugundua strategy — bado haijajengwa
├── config/risk.yaml            vigezo vya risk/cost (PD anahariri, hakuna code)
├── config/broker_costs.yaml    commission + gharama za usiku (PD)
├── config/data.yaml            vigezo vya data/symbols/splits kwa injini ijayo
├── src/rce/                    budget · cost · sizing · gate · engine · config
└── tests/rce/                  tests za spec — ziliandikwa KABLA ya code
```

## RCE

Mamlaka pekee ya **gharama**, **ukubwa wa position**, na **ruhusa ya kutrade**.

* Model **haikadirii** gharama. Inaipokea.
* Model **haiamui** ukubwa wala ruhusa.
* RCE **haiamui** entry wala mwelekeo.

RCE haitegemei chochote nje yake — inasoma config yake yenyewe (`src/rce/config.py`)
na YAML pekee. Sehemu nyingine yoyote ya mfumo ikibadilika au ikiondolewa, RCE
inabaki ikifanya kazi.

```
python -m pytest -q
```

## Injini ya kugundua strategy

`docs/DOCTRINE.md` inaelezea inachopaswa kuwa: ticks za bid/ask → bar builder →
features → regimes → events → generator → lango la uchumi → backtest → sakafu ya
kelele → models → holdout ya mara moja.

**Bado haijajengwa.** Doctrine ina sheria 13 zisizovunjika (§19) na maamuzi matatu
yanayosubiri PD (§21). Hakuna code itakayoandikwa kabla ya hayo.

Sheria ya kwanza inayotawala kila kingine (§2):

> Namba yoyote inayoingia kwenye uamuzi lazima **ipimwe na injini yenyewe**, kwenye
> mchakato huu, kabla ya kutumika. Hakuna constant inayorithiwa.
