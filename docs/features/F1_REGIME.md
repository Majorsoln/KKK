# F1 — REGIME — feature cards (PD 2026-08-03)

> **Hadhi:** kadi rasmi za familia F1, kwa mujibu wa `../DATA_FEATURE_STANDARD.md` §6.
> Hii ndiyo familia ya **mfano** — F2–F7 zitafuata muundo huu huu. Kadi zinaandikwa
> **KABLA** ya code na **KABLA** ya kuona namba yoyote (§3 ya `../RESEARCH_PLAN_R0.md`).

**Kazi ya F1:** kujibu swali la tabaka la UNDERSTANDING — *"soku liko katika hali gani, na
linaelekea wapi?"* Inalisha **HMM** na **Transformer** (§1.2 ya KAIROS-1).
**TF zake:** D1 · H4 · H2. Haiingii M30/M15 — hizo ni za F2/F3.

---

## 1. SHERIA ZA FAMILIA

1. **Kuhesabu kwa TF:** fomula moja kwenye TF tatu = **features TATU** kwenye bajeti, si moja.
   Hii ndiyo sababu F1 ina fomula 12 lakini features 34.
2. **Warm-up ni gharama halisi.** Window ndefu zaidi ya F1 ni `vol_pct_rank` (W=250 kwenye D1)
   + ATR(14) = **bars 264 za D1 ≈ miezi 13**. Mwaka wa kwanza wa data ni warm-up, **si training**.
   Kwa miaka 5 ya data, ni 20% inayopotea kabla ya label ya kwanza.
3. **Point-in-time kabisa:** percentile ranks, σ na HMM posteriors zote zinatumia data ya nyuma
   pekee (§6.1 sheria 2). Hakuna `rank` kwenye dataset nzima.
4. **As-of:** thamani inayotumika wakati wa uamuzi wa H1 ni ya bar ya **mwisho iliyofungwa** ya
   TF husika (§4.1).
5. **Chanzo kimoja cha ATR:** `ATR(14)` ya TF husika, function moja, inayoshirikiwa na F4.
   Haiandikwi upya hapa.
6. **NaN:** window haijajaa → `is_valid=false`, si sifuri (§6.1 sheria 7).

---

## 2. KADI

### F1.01 — `ret_z_{n}`
```yaml
name:        ret_z_5 · ret_z_20
family:      F1
tf:          D1 · H4 · H2                        # features 6
formula:     r_i   = log(close_i / close_{i-1})
             ret_z = ( Σ_{i=t-n+1..t} r_i ) / ( σ_r × √n )
             σ_r   = std(r, window=norm_window)  # rolling, nyuma PEKEE
window:      n ∈ {5, 20}  (+ norm_window=500 kwa σ)
inputs:      L2/<tf>[close]
hypothesis:  "Mwendo uliopimwa kwa volatility yake mwenyewe unatofautisha mwendelezo halisi
              na kelele. Bila kugawanya kwa σ, D1 ya XAUUSD na H2 ya EURUSD haziwezi
              kulinganishwa kwenye model moja."
expected_ic: "+ kwa D1/H4 (trend persistence). H2: HAIJULIKANI — tunapima |IC|."
cost:        O(1) rolling
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.02 — `trend_slope_atr`
```yaml
name:        trend_slope_atr
family:      F1
tf:          D1 · H4 · H2                        # features 3
formula:     slope = OLS slope ya close kwa bars n (x = 0..n-1)
             trend_slope_atr = slope × n / ATR(14)
window:      n = 20
inputs:      L2/<tf>[close, high, low]
hypothesis:  "Mwelekeo wa regression ukiwa umepimwa kwa ATR unasema 'soko limesogea ATR ngapi
              kwenye window hii' — kipimo cha nguvu ya trend kisichotegemea bei wala symbol."
expected_ic: "+ (mwelekeo wa trend unaendana na mwelekeo wa trade)"
cost:        O(1) rolling (Welford / sums)
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.03 — `trend_r2`
```yaml
name:        trend_r2
family:      F1
tf:          D1 · H4 · H2                        # features 3
formula:     R² ya regression ile ile ya F1.02        ∈ [0, 1]
window:      n = 20
inputs:      L2/<tf>[close]
hypothesis:  "Slope inasema MWELEKEO; R² inasema UBORA. Slope kubwa yenye R² ndogo ni soko
              lililoruka, si trend. Zikiwa pamoja zinatofautisha trend na choppiness —
              tofauti ambayo slope PEKEE haiwezi kuiona."
expected_ic: "+ ikichanganywa na slope; peke yake HAIJULIKANI (haina mwelekeo)"
cost:        O(1) (inatoka kwenye hesabu ile ile ya F1.02)
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.04 — `efficiency_ratio`
```yaml
name:        efficiency_ratio        # Kaufman ER
family:      F1
tf:          D1 · H4 · H2                        # features 3
formula:     ER = |close_t − close_{t-n}| / Σ_{i=t-n+1..t} |close_i − close_{i-1}|   ∈ [0,1]
window:      n = 20
inputs:      L2/<tf>[close]
hypothesis:  "Uwiano wa mwendo halisi na njia iliyotembewa. ER→1 = trend safi,
              ER→0 = kurudi-rudi. Ni scale-free KWA UJENZI (ratio ya vitu vya units sawa)
              na haihitaji normalization yoyote."
expected_ic: "+ kwenye setups za trend/breakout; − kwenye mean-reversion (PPO itatenganisha)"
cost:        O(1) rolling
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.05 — `vol_ratio`
```yaml
name:        vol_ratio
family:      F1
tf:          D1 · H4 · H2                        # features 3
formula:     vol_ratio = σ(r, 20) / σ(r, 100)
window:      20 na 100
inputs:      L2/<tf>[close]
hypothesis:  "Upanuzi vs mkazo wa volatility. >1 = soko linafunguka (breakout regime),
              <1 = linabana (compression, mara nyingi kabla ya upanuzi). Ratio, si σ yenyewe,
              kwa sababu σ ghafi si scale-free kati ya symbols."
expected_ic: "HAIJULIKANI — tunatarajia mwingiliano (interaction) na F1.04, si athari ya moja kwa moja"
cost:        O(1) rolling
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.06 — `vol_pct_rank`
```yaml
name:        vol_pct_rank
family:      F1
tf:          D1 · H4 · H2                        # features 3
formula:     rank ya ATR(14)[t] ndani ya ATR(14)[t-W..t] ÷ W        ∈ [0,1]
window:      W = 250   (⚠ warm-up ndefu zaidi ya F1 — §1 sheria 2)
inputs:      L2/<tf>[high, low, close]
hypothesis:  "Volatility ya sasa ikilinganishwa na historia YAKE. Percentile inaondoa tatizo la
              units kabisa na inavuka regime shifts — ATR ya pips 8 kwenye EURUSD ni kubwa,
              kwenye XAUUSD ni ndogo; rank inajua tofauti hiyo bila kuambiwa."
expected_ic: "− (volatility ya juu sana = mazingira mabaya kwa edge nyembamba)"
cost:        O(log W) kwa rolling order-statistic
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.07 — `range_pos`
```yaml
name:        range_pos
family:      F1
tf:          D1 · H4 · H2                        # features 3
formula:     (close_t − min(low, n)) / (max(high, n) − min(low, n))       ∈ [0,1]
window:      n = 20
inputs:      L2/<tf>[high, low, close]
hypothesis:  "Tuko wapi ndani ya range ya hivi karibuni. Karibu na 1/0 = kwenye ukingo
              (breakout au kukataliwa); katikati = hakuna taarifa ya muundo."
expected_ic: "+ kwa breakout, − kwa reversal — inategemea strategy. Tunapima kwa mgawanyo."
cost:        O(1) kwa monotonic deque
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.08 — `dd_atr`
```yaml
name:        dd_atr
family:      F1
tf:          D1 · H4 · H2                        # features 3
formula:     (max(close, n) − close_t) / ATR(14)
window:      n = 50
inputs:      L2/<tf>[close, high, low]
hypothesis:  "Umbali kutoka kilele cha hivi karibuni, kwa ATR. Inatofautisha 'trend inayoendelea'
              na 'trend iliyoanza kuvunjika' — hali ambayo slope pekee bado inaiita trend."
expected_ic: "− kwa BUY (drawdown kubwa = trend inadhoofika)"
cost:        O(1) kwa monotonic deque
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.09 — `dir_agreement`
```yaml
name:        dir_agreement
family:      F1
tf:          CROSS (D1+H4+H2 → thamani MOJA)     # feature 1
formula:     ( sign(trend_slope_atr_D1)
              + sign(trend_slope_atr_H4)
              + sign(trend_slope_atr_H2) ) / 3           ∈ {-1, -1/3, 1/3, 1}
window:      inarithi n=20 ya F1.02
inputs:      F1.02 kwenye TF tatu (as-of, §4.1)
hypothesis:  "Muunganiko wa TF ndio dhana kuu ya hierarchy ya KAIROS-1 (D1 bias → H4 trend →
              H2 regime). Feature hii inaipima MOJA KWA MOJA badala ya kutumaini model
              itaigundua yenyewe kutoka features 3 tofauti."
expected_ic: "+ (muunganiko = mazingira safi ya kuingia)"
cost:        O(1)
owner:       PD
added:       2026-08-03
status:      candidate
```

### F1.10 — `hmm_state_post_{k}`
```yaml
name:        hmm_state_post_0 · hmm_state_post_1        # k=3 states, MOJA imedondoshwa
family:      F1
tf:          D1 · H4                              # features 4  (H2 imeachwa: gharama vs faida)
formula:     Gaussian HMM (k=3) kwenye [r, |r|, ATR-normalized range]
             posterior = FILTERING (forward algorithm)   ⚠ SI smoothing
window:      fit kwenye train fold; filtering inaendelea point-in-time
inputs:      L2/<tf>[open, high, low, close]
hypothesis:  "Regime si feature moja — ni hali fiche inayoathiri features zote. HMM inatoa
              posterior ya hali, ambayo ni muhtasari mnene kuliko features ghafi."
expected_ic: "HAIJULIKANI — states hazina maana iliyopangwa; tunapima kwa |IC| na ablation"
cost:        GHALI — fit kwa kila fold
owner:       PD
added:       2026-08-03
status:      candidate
```
> **⚠ HATARI MBILI ZA KADI HII (soma §4).** (a) Posteriors ni **model output kama feature** —
> lazima ifitwe **ndani ya train fold pekee**. (b) `smoothing` (Baum-Welch posterior kwa
> sequence nzima) inatumia data ya **baadaye** — ni uvujaji. Ni **filtering** pekee.
> Posteriors za k zinajumlisha 1 → moja ni ya ziada, inadondoshwa.

### F1.11 — `hurst_dfa` *(candidate wa hiari)*
```yaml
name:        hurst_dfa
family:      F1
tf:          D1                                   # feature 1
formula:     DFA exponent kwenye returns, window ndefu
window:      250
inputs:      L2/D1[close]
hypothesis:  "H>0.5 = persistence (trend-following inalipa); H<0.5 = mean-reversion."
expected_ic: "+ kwa strategy za trend"
cost:        GHALI, na ni NDOGO KWA WINDOW FUPI — kelele nyingi
owner:       PD
added:       2026-08-03
status:      candidate (kipaumbele cha chini — ondoa kwanza bajeti ikibana)
```

### F1.12 — `ret_skew` *(candidate wa hiari)*
```yaml
name:        ret_skew
family:      F1
tf:          D1                                   # feature 1
formula:     skewness ya r kwa bars n
window:      n = 100
inputs:      L2/D1[close]
hypothesis:  "Umbo la distribution ya regime — soko lenye skew hasi lina tail-risk ya upande
              mmoja, jambo linaloathiri p_tp_first kwa mwelekeo."
expected_ic: "+ kwa BUY (skew chanya)"
cost:        O(1) rolling moments
owner:       PD
added:       2026-08-03
status:      candidate (kipaumbele cha chini)
```

---

## 3. MUHTASARI NA BAJETI

| Kadi | Fomula | TF | Features |
|---|---|---|---|
| F1.01 | `ret_z_{5,20}` | D1·H4·H2 | 6 |
| F1.02 | `trend_slope_atr` | D1·H4·H2 | 3 |
| F1.03 | `trend_r2` | D1·H4·H2 | 3 |
| F1.04 | `efficiency_ratio` | D1·H4·H2 | 3 |
| F1.05 | `vol_ratio` | D1·H4·H2 | 3 |
| F1.06 | `vol_pct_rank` | D1·H4·H2 | 3 |
| F1.07 | `range_pos` | D1·H4·H2 | 3 |
| F1.08 | `dd_atr` | D1·H4·H2 | 3 |
| F1.09 | `dir_agreement` | cross | 1 |
| F1.10 | `hmm_state_post` | D1·H4 | 4 |
| F1.11 | `hurst_dfa` | D1 | 1 |
| F1.12 | `ret_skew` | D1 | 1 |
| | | **JUMLA** | **34** |

**Ukaguzi wa bajeti** (§0.1 ya standard): pooled ≈ 10,900 labels ÷ 50 = **≈218 features**
kwa familia saba = **≈31 kwa familia**. F1 ina **34** — imevuka kwa 3.

**Hii si hitilafu, ni hali inayotarajiwa.** Kadi zinaandikwa kama *candidates*; **R2 na R3**
ndizo zinazokata. F1.11 na F1.12 zimewekwa alama ya kipaumbele cha chini kwa makusudi — ndizo
za kwanza kuondoka. Kilichokatazwa ni **kujenga zote 34 na kuziacha** bila screening.

---

## 4. HATARI MAALUM ZA F1

| # | Hatari | Kinga |
|---|---|---|
| 1 | **HMM smoothing = uvujaji.** Posterior ya sequence nzima inajua siku zijazo. | **Filtering pekee** (forward). Sentinel ya §4.2 inaikamata ikiwa imekosewa. |
| 2 | **HMM inafitwa kwenye data.** Ni model ndani ya model. | Fit **ndani ya train fold**; kamwe kwenye dataset nzima. Fold mpya = fit mpya. |
| 3 | **Percentile rank ya global** — kosa la kawaida kabisa. | Rolling W bars nyuma pekee (§6.1 sheria 2). |
| 4 | **Warm-up unaliwa kimya.** D1 W=250 = miezi 13. | Bars zisizo na window kamili: `is_valid=false`. Ripoti ya R0 inaonyesha labels zilizopotea. |
| 5 | **Multicollinearity ya ndani.** F1.02/F1.03/F1.04 zote zinapima "trend". | R3 (clustering @ \|ρ\|≥0.80) itachagua mwakilishi. Tunatarajia hizi tatu ziwe cluster moja. |
| 6 | **TF tatu za feature moja ni correlated.** D1 na H4 slope zinafanana. | R3 vivyo hivyo. Ikitokea D1 pekee inatosha, ni **ushindi** — data ndogo, warm-up fupi. |

---

## 5. INAYOPIMWA KWENYE R2 (pre-registration)

Kabla ya kukimbiza chochote, hivi ndivyo tulivyotangaza:

1. **Tunatarajia F1.02 + F1.03 + F1.04 ziwe cluster MOJA.** Zikiwa hazikuunganiki, dhana yetu
   kuhusu "trend" ina kasoro — hilo ni tokeo la kuvutia, si kosa.
2. **F1.09 (`dir_agreement`) ndiyo mtihani wa hierarchy ya KAIROS-1.** Isipokuwa na IC, dhana ya
   msingi ya "D1 bias → H4 trend → H2 regime" haina uthibitisho kwenye data yetu. Hiyo ni
   **LESSON kubwa**, na inagusa design ya §1.2 ya KAIROS-1 — si feature moja tu.
3. **F1.10 (HMM) inalinganishwa na F1 nzima bila HMM.** Ikiwa ΔEV_R ≈ 0 kwenye R7, HMM inaondoka
   kwenye pipeline — pamoja na gharama yake yote ya fitting.
4. **Features zenye `expected_ic: HAIJULIKANI` zinapimwa kwa \|IC\|**, si IC yenye ishara.
   Zilizotangazwa na ishara zinapimwa kwa **ishara ile ile** — ishara ikigeuka, ni onyo la
   over-fitting, si ugunduzi.

Vigezo: `ic_min` 0.02 · `ic_sign_stability` 0.60 · permutation test · `corr_cluster` 0.80
(zote `config/data.yaml`).

---

## 6. INAYOFUATA
`F2_STRUCTURE.md` — familia yenye hatari kubwa zaidi: patterns nyingi (sweep, order block, MSS)
ni **hadithi**, si taarifa, hadi zithibitishwe. Kadi zake zitahitaji fomula **zisizo na utata**
kwa kila pattern — kama haiwezi kuandikwa kama fomula, haiwezi kupimwa, na haiingii.
