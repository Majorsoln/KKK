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

> **Kufunga upya (supersession).** Ripoti ya ushahidi ikijengwa upya, hash yake inahama
> hata kama namba zilizomo hazikubadilika — `built_at`, `code_rev` na `config_hash` zote
> zinabadilika. Mstari wa zamani hauwezi kufutwa (faili ni la kuongezwa tu), kwa hiyo PD
> anaweka **mstari MPYA wa kipengele kile kile, ukielekeza faili lile lile**. Lango
> linabadilisha lawama ya mstari wa zamani kuwa `imepitwa na #N` — inaonekana bado, lakini
> haizuii `PASS`. Masharti manne, yote ya lazima: kipengele kile kile · faili lile lile ·
> nambari kubwa zaidi · **hash ya mrithi inalingana na faili lililopo sasa**. Mrithi
> aliyepitwa naye hapitishi mtu — lango linaendelea kulia, kama inavyopaswa.
>
> Sababu: lango lisilo na njia ya kurudi kwenye `PASS` lingesema FAIL milele, na lango
> linalolia daima linafundisha msomaji kulipuuza. Hilo ni hatari kuliko kutokuwa na lango.

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
| 12 | 2026-08-13T09:22:13+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | RS-04 | VERIFIED | `sha256:0be747840` | `a9fb42b347b0a78d` | research\reports\r1\r1_summary.json | `7b5153fc9345f06d` | jiometri inashikilia: cells 23/25 chini ya sl/(sl+tp), na tofauti inashuka SL ikipanuka (-0.042 kwa 0.5 hadi -0.001 kwa 2.0) - saini ya spread, si drift; timeout 2.79%; utulivu 0.409-0.428 kwa 2016-2023 |
| 13 | 2026-08-13T09:22:13+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-09 | VERIFIED | `sha256:0be747840` | `a9fb42b347b0a78d` | research\reports\r1\r1_summary.json | `7b5153fc9345f06d` | labels 52,321 kwa path ya ticks, bila ticks 0; touch kwa bei ya kufungia; gap-honest imepimwa kwa touch_past_pips p99 14.59 |
| 14 | 2026-08-13T09:22:14+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-10 | VERIFIED | `sha256:0be747840` | `a9fb42b347b0a78d` | research\reports\r1\r1_summary.json | `7b5153fc9345f06d` | grid 5x5 kamili: cells 1,308,025 = points 52,321 x 25 sawasawa; timeout ni darasa la tatu lenye terminal return, si kutupwa |
| 15 | 2026-08-13T09:22:14+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-11 | VERIFIED | `sha256:0be747840` | `a9fb42b347b0a78d` | research\reports\r1\r1_summary.json | `7b5153fc9345f06d` | horizon moja (bars 24); class balance imeripotiwa kwa cell na kwa mwaka, haijasawazishwa; timeout 2.79% imeripotiwa |
| 16 | 2026-08-13T09:22:15+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-21 | LESSON | `sha256:0be747840` | `a9fb42b347b0a78d` | research\reports\r1\r1_summary.json | `7b5153fc9345f06d` | mkataba wa bei umethibitishwa: mid-vs-trade ni 0.02-0.10 ATR, si 0.003 - uamuzi wa mid unashikilia. LAKINI tie-break ya SL-kwanza HAIWEZI kuwaka kwa grid hii (BUY: SL na TP zote kwa bid); sheria imesainiwa lakini haijaguswa na data hata mara moja |
| 17 | 2026-08-13T09:22:37+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | K1-07 | VERIFIED | `sha256:0be747840` | `a9fb42b347b0a78d` | research\reports\r1\r1_summary.json | `7b5153fc9345f06d` | fill bootstrap imepimwa: stop touch 757,424, ndani ya cap 76.06% pekee; limit p50 0.13; market prior 0.98 haikisiwi kwa historia - inakalibiwa demo/live |
| 18 | 2026-08-13T09:39:20+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-20 | APPROVED | `sha256:0be747840` | `1f59b8f33e9d147b` | research\reports\r1\setup_rates.json | `6e3fe701b5cec71f` | kufunga upya baada ya detect-setups kuandika faili upya (labels.bat hatua 1/3). SI pre-registration mpya: pre-registration ni sahihi #11 kwenye commit f62f3e1 ya 2026-08-11, kabla build-labels haijawahi kuendeshwa - iko kwenye git. Sheria haijabadilika: config-hash --sections --since f62f3e1 inaonyesha `labels` pekee imebadilika (m1_check_frac); setups, quality, splits zote sawa |
| 19 | 2026-08-13T22:43:44+00:00 | Japhet Joseph Lemma <majorsoln@gmail.com> | DF-20 | APPROVED | `sha256:0be747840` | `07d0b8e777321e30` | research\reports\r1\cost_audit.json | `ba88bca8dc3a2f89` | T3 pre-registration: SR* 0.7 (bajeti configs 7.5, MinBTL); kappa 0.50 (n_max 142/mwaka); cell 2.0/3.0. NAKIRI: cell imechaguliwa BAADA ya kuona jedwali la EV - ni uteuzi juu ya label (4.3). Bar iliyotangazwa +0.0300 p_tp = 0.0065 hadi breakeven + 0.0235 delta_MER; N_req 3,553 dhidi ya N_eff 10,168 iliyopimwa |
