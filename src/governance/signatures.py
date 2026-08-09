"""Sahihi ya PD — utaratibu wenye ushahidi, si neno la mdomo.

§0 ya IMPLEMENTATION_PLAN inasema `VERIFIED` inapandishwa na **PD pekee**, juu ya
ushahidi. Hadi leo hilo lilikuwa neno lisilo na maana ya kiufundi: hakuna
mahali sahihi inakaa, na hakuna kinachozuia kipengele kupanda `VERIFIED` bila
mtu yeyote kukiangalia.

**Sahihi ni COMMIT ya PD.** Si sanduku la kutia alama, si ujumbe wa gumzo —
mstari kwenye `docs/SIGNATURES.md` uliowekwa na `scripts\\sign.bat`, ukiwa
umecommit kwa **utambulisho wa git wa PD** kwenye mashine yake. Kilichofanya
hii kuwa sahihi ya kweli, si maandishi tu, ni vitu vinne inavyofunga pamoja:

```
NANI       git user.name/user.email ya mashine ya PD (author wa commit)
LINI       muda wa commit — na MFUATANO wake kwenye historia (lango G4/RS-01)
NINI       ID ya rejista + uamuzi (VERIFIED / LESSON / APPROVED)
KWA NINI   config_hash + code_rev + SHA256 ya faili la ushahidi
```

`config_hash` na SHA256 ya ushahidi ndizo zinazozuia hila ya kawaida zaidi:
kusaini ripoti moja, kisha kubadilisha vizingiti au kuandika ripoti upya.
Sahihi ikishawekwa, ripoti ikibadilika, `verify` inaikataa.

Kwa **pre-registration** (RS-01, mfano sheria ya setup ya §4.3): sahihi ya
`APPROVED` lazima itangulie kwenye historia ya git kabla ya matokeo yoyote —
na commit ndiyo inayoithibitisha, kwa sababu tarehe ya commit haiwezi
kughushiwa bila kuandika upya historia (jambo linaloonekana).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Uamuzi unaoruhusiwa. Hakuna "sawa" wala "nimeona" — kila mmoja una maana
# moja tu kwenye §0 ya IMPLEMENTATION_PLAN.
DECISIONS: dict[str, str] = {
    "VERIFIED": "kipengele cha rejista kimekaguliwa kwa ushahidi na kimekubaliwa",
    "LESSON": "eneo lilipimwa, halikufaulu, sababu imeandikwa — jibu halali",
    "APPROVED": "pre-registration: vigezo/sheria imekubaliwa KABLA ya matokeo (RS-01)",
    "REJECTED": "ushahidi umeonekana hautoshi — kinabaki IMPLEMENTED",
}

HASH_PREFIX = 16          # herufi za hash zinazoandikwa kwenye jedwali
LEDGER = Path("docs/SIGNATURES.md")
PLAN = Path("docs/IMPLEMENTATION_PLAN.md")

_ROW = re.compile(r"^\|\s*(\d+)\s*\|")
_PD_LINE = re.compile(r"^\*\*PD:\*\*\s*`([^`]+)`", re.MULTILINE)
# Prefix inaruhusu namba (`K1-07`) — si herufi pekee. Kikomo cha awali
# `[A-Z]{1,4}` kilikuwa kikiacha familia nzima ya K1 nje ya rejista kimya.
_ID = re.compile(r"\b([A-Z][A-Z0-9]{0,3}-\d{2})\b")
_RANGE = re.compile(r"\b([A-Z][A-Z0-9]{0,3})-(\d{2})\.\.(\d{2})\b")


class SignatureError(RuntimeError):
    """Sahihi haiwezi kuwekwa au haikubaliki wakati wa uthibitisho."""


@dataclass
class Signature:
    """Mstari mmoja wa `docs/SIGNATURES.md` = uamuzi mmoja wa PD."""

    number: int
    signed_at: str
    signer: str
    item: str
    decision: str
    config_hash: str
    code_rev: str
    evidence: str
    evidence_sha256: str
    reason: str

    def to_row(self) -> str:
        # Hash zimekatwa hadi `HASH_PREFIX` ili jedwali lisomeke na mtu. Bits 64
        # hazitoshi dhidi ya mshambuliaji anayetengeneza collision, lakini si
        # hilo linalolindwa hapa: kinacholindwa ni **ripoti kubadilika bila mtu
        # kugundua** (kuandikwa upya, vizingiti kubadilishwa, faili kubadilishwa
        # nafasi). Kinga dhidi ya kughushi kwa makusudi ni historia ya git ya
        # faili hili lenyewe, si urefu wa hash.
        return (
            f"| {self.number} | {self.signed_at} | {self.signer} | {self.item} | "
            f"{self.decision} | `{self.config_hash[:HASH_PREFIX]}` | "
            f"`{self.code_rev[:HASH_PREFIX]}` | "
            f"{self.evidence or '—'} | `{self.evidence_sha256[:HASH_PREFIX] or '—'}` | "
            f"{self.reason} |"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "signed_at": self.signed_at,
            "signer": self.signer,
            "item": self.item,
            "decision": self.decision,
            "config_hash": self.config_hash,
            "code_rev": self.code_rev,
            "evidence": self.evidence,
            "evidence_sha256": self.evidence_sha256,
            "reason": self.reason,
        }


# --------------------------------------------------------------------------
# Utambulisho na ushahidi
# --------------------------------------------------------------------------


def git_identity(root: Path | None = None) -> str:
    """`user.name <user.email>` ya mashine hii — huyu ndiye anayesaini."""
    parts = []
    for key in ("user.name", "user.email"):
        try:
            value = subprocess.run(
                ["git", "config", "--get", key],
                cwd=str(root or Path.cwd()),
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            value = ""
        parts.append(value)
    name, email = parts
    if not name or not email:
        raise SignatureError(
            "utambulisho wa git haujawekwa — sahihi isiyo na mwenyewe si sahihi.\n"
            '  git config --global user.name "Jina Lako"\n'
            '  git config --global user.email "barua@yako"'
        )
    return f"{name} <{email}>"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# Rejista: ID zinazoruhusiwa
# --------------------------------------------------------------------------


def register_ids(plan_path: Path | None = None) -> set[str]:
    """ID zote za rejista (§3) — sahihi haiwezi kutaja kipengele kisichokuwepo."""
    text = Path(plan_path or PLAN).read_text(encoding="utf-8")
    ids: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        head = line.split("|")[1].strip().strip("`*")
        for prefix, start, end in _RANGE.findall(head):
            ids.update(f"{prefix}-{n:02d}" for n in range(int(start), int(end) + 1))
        ids.update(_ID.findall(head))
    if not ids:
        raise SignatureError(f"rejista haikusomeka kutoka {plan_path or PLAN}")
    return ids


# --------------------------------------------------------------------------
# Ledger
# --------------------------------------------------------------------------


def declared_pd(path: Path | None = None) -> str:
    """Utambulisho wa PD ulitangazwa kwenye kichwa cha ledger.

    Bila hii, mtu yeyote mwenye repo angeweza kuandika `VERIFIED` — ikiwemo
    mtekelezaji, ikiwemo model. Ni tangazo la wazi, si siri: linakaa kwenye git,
    na kulibadilisha ni commit inayoonekana kama nyingine yoyote.
    """
    target = Path(path or LEDGER)
    if not target.is_file():
        return ""
    match = _PD_LINE.search(target.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else ""


def _email_of(identity: str) -> str:
    """Sehemu ya `<...>`, herufi ndogo — hii ndiyo inayotambulisha mtu.

    Barua pepe ndiyo sehemu THABITI ya utambulisho wa git: inatolewa na mfumo,
    ni ya kipekee, na haibadiliki kwa mapendeleo. Jina ni mapambo.
    """
    start = identity.find("<")
    end = identity.find(">", start + 1)
    if start == -1 or end == -1:
        return identity.strip().casefold()
    return identity[start + 1 : end].strip().casefold()


def _name_of(identity: str) -> str:
    start = identity.find("<")
    return (identity if start == -1 else identity[:start]).strip().casefold()


def load(path: Path | None = None) -> list[Signature]:
    target = Path(path or LEDGER)
    if not target.is_file():
        return []
    out: list[Signature] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if not _ROW.match(line):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) < 10:
            continue
        out.append(
            Signature(
                number=int(cells[0]),
                signed_at=cells[1],
                signer=cells[2],
                item=cells[3],
                decision=cells[4],
                config_hash=cells[5],
                code_rev=cells[6],
                evidence="" if cells[7] == "—" else cells[7],
                evidence_sha256="" if cells[8] == "—" else cells[8],
                reason=cells[9],
            )
        )
    return out


def append(
    item: str,
    decision: str,
    reason: str,
    config_hash: str,
    code_rev: str,
    evidence: Path | None = None,
    signer: str | None = None,
    ledger: Path | None = None,
    plan: Path | None = None,
    root: Path | None = None,
) -> Signature:
    """Weka sahihi mpya. Inakataa mapema badala ya kuandika kitu kisicho na maana."""
    decision = decision.upper().strip()
    if decision not in DECISIONS:
        raise SignatureError(
            f"uamuzi `{decision}` haujulikani — chagua: {', '.join(DECISIONS)}"
        )
    item = item.upper().strip()
    known = register_ids(plan)
    if item not in known:
        raise SignatureError(
            f"`{item}` haipo kwenye rejista ya §3. Sahihi haiwezi kutaja kipengele "
            "kisichokuwepo — kwanza kiongeze kwenye mpango."
        )
    if not reason.strip():
        raise SignatureError(
            "sahihi bila sababu ni alama tupu — andika unachokiona kwenye ushahidi"
        )

    evidence_path = ""
    evidence_hash = ""
    if evidence is not None:
        evidence = Path(evidence)
        if not evidence.is_file():
            raise SignatureError(f"faili la ushahidi halipo: {evidence}")
        evidence_hash = sha256_of(evidence)
        try:
            evidence_path = str(evidence.relative_to(Path(root or Path.cwd())))
        except ValueError:
            evidence_path = str(evidence)
    elif decision == "VERIFIED":
        raise SignatureError(
            "`VERIFIED` inahitaji faili la ushahidi (§0 sheria ya 3: PD anaona ripoti "
            "au test ikipita — si maelezo ya mdomo). Tumia --evidence <njia>."
        )

    existing = load(ledger)
    signature = Signature(
        number=len(existing) + 1,
        signed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        signer=signer or git_identity(root),
        item=item,
        decision=decision,
        config_hash=config_hash,
        code_rev=code_rev,
        evidence=evidence_path,
        evidence_sha256=evidence_hash,
        reason=reason.strip().replace("|", "/").replace("\n", " "),
    )
    _write(signature, ledger)
    return signature


def _write(signature: Signature, ledger: Path | None = None) -> Path:
    target = Path(ledger or LEDGER)
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_HEADER, encoding="utf-8")
    with target.open("a", encoding="utf-8") as handle:
        handle.write(signature.to_row() + "\n")
    return target


_HEADER = """# SAHIHI ZA PD — kumbukumbu isiyofutika

**PD:** `JINA LAKO <barua@yako>`

> Mstari hapo juu ni tangazo la **nani ana mamlaka ya kusaini**. Ubadilishe mara
> moja uwekapo utambulisho wako halisi wa git (`git config user.name/user.email`).
> `VERIFIED`, `APPROVED` na `LESSON` zinazotoka kwa mtu mwingine yeyote —
> mtekelezaji, model, mtu wa timu — **zinakataliwa na lango G14.**

> **Faili hili ni la kuongezwa tu.** Mstari ukishawekwa hauhaririwi wala kufutwa;
> uamuzi ukibadilika, unawekwa mstari MPYA. Historia ya kubadili mawazo ni sehemu
> ya ushahidi, si aibu.

Sahihi haiwekwi kwa mkono. Inawekwa kwa:

```cmd
scripts\\sign.bat <ID> <UAMUZI> --evidence <faili> --reason "unachokiona"
```

na inakuwa halali pale tu **PD anapocommit** mstari huo kwa utambulisho wake wa git.
Author wa commit + muda wake + `config_hash` + SHA256 ya ushahidi ndivyo vinavyofanya
mstari huu kuwa sahihi badala ya maandishi. `python -m src.governance.cli verify`
inakagua kila kitu (lango G14).

| # | Tarehe (UTC) | PD | Kipengele | Uamuzi | config_hash | code_rev | Ushahidi | SHA256 | Sababu |
|---|---|---|---|---|---|---|---|---|---|
"""


# --------------------------------------------------------------------------
# Uthibitisho (lango G14)
# --------------------------------------------------------------------------


@dataclass
class VerifyReport:
    checked: int = 0
    problems: list[str] = field(default_factory=list)
    verified_items: set[str] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def render(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        lines = [
            f"sahihi: {status} · zilizokaguliwa {self.checked} · "
            f"vipengele VERIFIED {len(self.verified_items)}"
        ]
        lines += [f"  ! {p}" for p in self.problems]
        lines += [f"  · {n}" for n in self.notes]
        return "\n".join(lines)


def verify(
    ledger: Path | None = None,
    plan: Path | None = None,
    root: Path | None = None,
    check_evidence: bool = True,
) -> VerifyReport:
    """Lango G14 — kila sahihi inatajwa na rejista, na ushahidi wake haujabadilika."""
    report = VerifyReport()
    known = register_ids(plan)
    base = Path(root or Path.cwd())
    pd_identity = declared_pd(ledger)
    seen_numbers: set[int] = set()

    for signature in load(ledger):
        report.checked += 1
        # Matatizo YA SAHIHI HII pekee. Sahihi yenye tatizo lolote haipandishi
        # hadhi — vinginevyo `verified_items` ingesema uwongo hata wakati lango
        # linapiga kelele, na kila kinachotegemea orodha hiyo kingerithi uwongo.
        before = len(report.problems)

        if signature.number in seen_numbers:
            report.problems.append(f"#{signature.number}: nambari imerudiwa")
        seen_numbers.add(signature.number)

        if signature.item not in known:
            report.problems.append(
                f"#{signature.number}: `{signature.item}` haipo kwenye rejista ya §3"
            )
        if signature.decision not in DECISIONS:
            report.problems.append(
                f"#{signature.number}: uamuzi `{signature.decision}` haujulikani"
            )
        if "<" not in signature.signer:
            report.problems.append(
                f"#{signature.number}: mwenye sahihi hana barua pepe — si utambulisho wa git"
            )
        elif pd_identity and signature.decision in ("VERIFIED", "APPROVED", "LESSON"):
            # Hii ndiyo kinga kuu: `VERIFIED` ni mamlaka ya PD PEKEE (§1.1).
            # Mtekelezaji — au model — akiendesha `sign`, utambulisho wake ndio
            # unaoandikwa, na lango linaikataa. Huwezi kujisainia mwenyewe.
            if _email_of(signature.signer) != _email_of(pd_identity):
                report.problems.append(
                    f"#{signature.number}: `{signature.decision}` imesainiwa na "
                    f"`{signature.signer}`, si PD (`{pd_identity}`). Mamlaka ya "
                    "VERIFIED/APPROVED/LESSON ni ya PD pekee (§1.1)."
                )
            elif _name_of(signature.signer) != _name_of(pd_identity):
                # Barua pepe inalingana; jina la kuonyesha halilingani. Hilo si
                # suala la mamlaka — `git config user.name` ni maandishi ya
                # mtumiaji, yanayoweza kuwa "Japhet joseph lemma" leo na
                # "Japhet Joseph Lemma" kesho. Kufelisha lango kwa herufi kubwa
                # kungezuia PD halali bila kuzuia mtu asiye halali hata mmoja.
                # Tofauti inaandikwa ili ionekane, si kuzuia.
                report.notes.append(
                    f"#{signature.number}: jina `{signature.signer}` linatofautiana na "
                    f"tangazo `{pd_identity}` (barua pepe ni ile ile — si suala la mamlaka)"
                )
        if not signature.reason:
            report.problems.append(f"#{signature.number}: hakuna sababu")

        if check_evidence and signature.evidence:
            path = base / signature.evidence
            if not path.is_file():
                report.problems.append(
                    f"#{signature.number}: ushahidi haupo tena ({signature.evidence})"
                )
            elif not sha256_of(path).startswith(signature.evidence_sha256):
                report.problems.append(
                    f"#{signature.number}: **ushahidi umebadilika baada ya kusainiwa** "
                    f"({signature.evidence}) — sahihi haifuniki faili hili tena"
                )

        if len(report.problems) != before:
            continue        # sahihi hii ina tatizo — haihesabiki
        if signature.decision == "VERIFIED":
            report.verified_items.add(signature.item)
        elif signature.decision == "REJECTED":
            report.verified_items.discard(signature.item)

    return report


def pending(
    items: Iterable[str], ledger: Path | None = None
) -> list[str]:
    """Vipengele visivyo na sahihi bado — ndio orodha halisi ya kazi ya PD."""
    signed = {s.item for s in load(ledger) if s.decision in ("VERIFIED", "LESSON")}
    return sorted(set(items) - signed)
