# ELITEFX

Repo hii ina kitu kimoja: **RCE** — Risk & Cost Engine.

```
├── docs/RISK_COST_ENGINE.md    spec ya RCE — HAIGUSWI
├── config/risk.yaml            vigezo vya risk/cost (PD anahariri, hakuna code)
├── config/broker_costs.yaml    commission + gharama za usiku (PD)
├── src/rce/                    budget · cost · sizing · gate · engine · config
└── tests/rce/                  tests za spec — ziliandikwa KABLA ya code
```

## RCE

Mamlaka pekee ya **gharama**, **ukubwa wa position**, na **ruhusa ya kutrade**.

* Model **haikadirii** gharama. Inaipokea.
* Model **haichagui** lots. Inaomba, RCE inaamua.
* Gharama inatoka kwenye data ya broker, si kwenye dhana.

Spec iko `docs/RISK_COST_ENGINE.md`. Tests zilizoandikwa kabla ya code ziko
`tests/rce/`, na zinapima dhidi ya `config/risk.yaml` **halisi** — kigezo
kikibadilishwa bila spec kubadilika, test inafeli.

## Kuendesha

```
pip install -e ".[dev]"
python -m pytest -q
```

## Kilichofuata

Injini ya kugundua strategy **bado haijajengwa**. Mbinu itakayotumika
inajadiliwa; hakuna code ya utafutaji kwenye repo hii kwa sasa.
