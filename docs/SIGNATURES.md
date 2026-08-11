# SAHIHI ZA PD — kumbukumbu isiyofutika

**PD:** `Japhet Joseph Lemma <majorsoln@gmail.com>`

> Mstari hapo juu ni tangazo la **nani ana mamlaka ya kusaini**. Ubadilishe mara
> moja uwekapo utambulisho wako halisi wa git (`git config user.name/user.email`).
> `VERIFIED`, `APPROVED` na `LESSON` zinazotoka kwa mtu mwingine yeyote —
> mtekelezaji, model, mtu wa timu — **zinakataliwa na lango G14.**

> **Faili hili ni la kuongezwa tu.** Mstari ukishawekwa hauhaririwi wala kufutwa;
> uamuzi ukibadilika, unawekwa mstari MPYA. Historia ya kubadili mawazo ni sehemu
> ya ushahidi, si aibu.

Sahihi haiwekwi kwa mkono. Inawekwa kwa:

```cmd
scripts\sign.bat <ID> <UAMUZI> --evidence <faili> --reason "unachokiona"
```

na inakuwa halali pale tu **PD anapocommit** mstari huo kwa utambulisho wake wa git.
Author wa commit + muda wake + `config_hash` + SHA256 ya ushahidi ndivyo vinavyofanya
mstari huu kuwa sahihi badala ya maandishi. `python -m src.governance.cli verify`
inakagua kila kitu (lango G14).

> **Kuhusu #1–#2 na #3–#4 (2026-08-09).** Ni maamuzi mawili yale yale, yakiwa yamewekwa
> mara mbili. #1–#2 zilisainiwa kabla ya `git pull`, kwa hiyo `code_rev` yake (`7e0795a`)
> ni commit ambapo `quality.excluded_ranges` **haipo kabisa** na `min_coverage` bado ni
> 0.995 — zinaidhinisha kitu kisichoonekana pale zinapoelekeza. #3–#4 zina `8110cb5` /
> `7ad62af`: config inayobeba maamuzi yenyewe. **#3–#4 ndizo za kutumia.** #1–#2 zinabaki
> kwa sababu faili hili ni la kuongezwa tu, na kwa sababu mfuatano wenyewe ni ushahidi:
> unaonyesha kilichotokea, si kilichotakiwa kutokea.

| # | Tarehe (UTC) | PD | Kipengele | Uamuzi | config_hash | code_rev | Ushahidi | SHA256 | Sababu |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-08-09T18:42:10+00:00 | Japhet joseph lemma <majorsoln@gmail.com> | DF-05 | APPROVED | `sha256:9981eb218` | `7e0795afabef9068` | — | `—` | 2023 ya Toleo B inaondoka: chanzo, si soko; labels za touch zingedanganya |
| 2 | 2026-08-09T18:42:10+00:00 | Japhet joseph lemma <majorsoln@gmail.com> | DF-05 | APPROVED | `sha256:9981eb218` | `7e0795afabef9068` | — | `—` | min_coverage 0.95 — kizingiti cha 0.995 kilikuwa kinapima ukamilifu wa feed, si biashara |
| 3 | 2026-08-09T18:51:40+00:00 | Japhet joseph lemma <majorsoln@gmail.com> | DF-05 | APPROVED | `sha256:8110cb5bd` | `7ad62afbee183c02` | — | `—` | 2023 ya Toleo B inaondoka: chanzo, si soko; labels za touch zingedanganya |
| 4 | 2026-08-09T18:51:40+00:00 | Japhet joseph lemma <majorsoln@gmail.com> | DF-05 | APPROVED | `sha256:8110cb5bd` | `7ad62afbee183c02` | — | `—` | min_coverage 0.95 - kizingiti cha 0.995 kilikuwa kinapima ukamilifu wa feed, si biashara |
| 5 | 2026-08-10T21:28:30+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-05 | VERIFIED | `sha256:8110cb5bd` | `46f5f33d4d82778a` | research\reports\quality\quality_report.json | `83f4e7739de35f04` | siku 33,440/34,781 (96.1%); kufeli kubwa ni uamuzi wangu wa 2023 (912); checks saba zote chini ya 0.72%; nimekagua sababu zote |
| 6 | 2026-08-10T21:28:30+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | RS-03 | VERIFIED | `sha256:8110cb5bd` | `46f5f33d4d82778a` | research\reports\quality\calendar_vs_assumed.json | `8de706017f899090` | kalenda inatoka kwenye data; siku 0 zilizotarajiwa bila data; Jumamosi 0; sikukuu 16 zote ni 25Des/1Jan |
| 7 | 2026-08-10T21:28:31+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-06 | VERIFIED | `sha256:8110cb5bd` | `46f5f33d4d82778a` | research\reports\quality\variant_comparison.json | `db6175ee864aa5f1` | symbols 12 zina TF 7; Toleo A na B zinatoa schema moja baada ya normalization |
| 8 | 2026-08-10T21:28:31+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-07 | VERIFIED | `sha256:8110cb5bd` | `46f5f33d4d82778a` | research\reports\quality\splits.json | `7d4d94555f292411` | as-of imethibitishwa kwa mfano wa spec 4.1 na juu ya L2 iliyoandikwa diski |
| 9 | 2026-08-10T21:28:31+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-08 | VERIFIED | `sha256:8110cb5bd` | `46f5f33d4d82778a` | research\reports\quality\splits.json | `7d4d94555f292411` | sentinel ya uvujaji: PASS, leaked=0, kwenye EURUSD na synthetic |
| 10 | 2026-08-10T21:28:32+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-14 | VERIFIED | `sha256:8110cb5bd` | `46f5f33d4d82778a` | research\reports\quality\splits.json | `7d4d94555f292411` | G2 PASS: folds 5 zote ndani ya TRAIN+VAL; holdout 2024-04-01+ haijaguswa; embargo bars 36 |
| 11 | 2026-08-11T16:53:49+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-20 | APPROVED | `sha256:4ce176875` | `f62f3e163a7ed377` | research\reports\r1\setup_rates.json | `9177bf997b8325c5` | SETUP-v1 pre-registration: gates tatu mechanical; min_atr_mult 2.5 imetunwa kwa RATE kabla ya labels (sweep 1.0=26% ... 2.5=4.46%); pooled 4.46% setups 25,374 dhidi ya lengo 5%; symbols zote 12 kati ya 3.9-4.9% - kigezo ni scale-free; control 0.05 kwa nguvu ya kitakwimu; siku zilizofeli R0 zimeondolewa - EURCHF/GBPJPY/XAUUSD zinapoteza ~6,000 bars kila moja (2023) |
