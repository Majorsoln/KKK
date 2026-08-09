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
