"""Breaking-gate regression tests. Run: python tests/test_breaking.py
An anime listicle must NEVER break, even when corroborated.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rank import score_items, pick_breaking, _is_evergreen

CFG = {"breaking_whitelist": ["BBC World", "BellumActaNews"],
       "breaking_keywords": ["breaking", "urgent", "coup", "explosion", "earthquake"]}

def _item(title, source, pillar="geopolitics", corroborated=False, cat=None):
    it = {"title": title, "summary": "", "link": f"https://x/{abs(hash(title)) % 99999}",
          "source": source, "outlet": source, "pillar": pillar, "trust": 3,
          "ts": 9999999999, "_score": 5}
    if corroborated:
        it["_corroborated"] = True
    if cat is not None:
        it["_cat"] = cat
    return it

fails = 0
def check(name, cond):
    global fails
    print(("OK  " if cond else "FAIL"), name)
    if not cond:
        fails += 1

# 1. corroborated anime listicle is NOT breaking
anime = [_item("5 Greatest Time Travel Anime of All Time, Ranked", "CBR",
              "entertainment", True),
         _item("10 Best Time Travel Anime of All Time, Ranked", "ScreenRant",
              "entertainment", True)]
check("anime listicle never breaks", pick_breaking(anime, CFG) == [])

# 2. corroborated geopolitics still breaks
coup = [_item("Equatorial Guinea says it foiled coup attempt", "africaintel",
              "geopolitics", True)]
picks = pick_breaking(coup, CFG)
check("real corroborated story breaks",
      len(picks) == 1 and "coup" in picks[0]["title"].lower())

# 3. evergreen wording excluded even outside entertainment
ever = [_item("10 greatest naval battles of all time ranked", "BBC World",
              "geopolitics", True)]
check("evergreen ranking never breaks", pick_breaking(ever, CFG) == [])
check("evergreen detector", _is_evergreen("5 Greatest Anime of All Time, Ranked")
      and not _is_evergreen("Explosions heard on Qeshm Island"))

# 4. whitelist + keyword path still works for fresh events
wire = [_item("BREAKING: explosions heard on Qeshm Island", "BellumActaNews")]
check("whitelist+keyword breaks",
      len(pick_breaking(wire, CFG)) == 1)

# 5. score_items actually corroborates two similar real headlines
pair = [_item("Equatorial Guinea says it foiled coup attempt against Obiang", "africaintel"),
        _item("Equatorial Guinea claims to have foiled coup attempt", "BBC World")]
scored = score_items(pair)
check("corroboration detected",
      all(s.get("_corroborated") for s in scored))
check("corroborated pair breaks", len(pick_breaking(scored, CFG)) == 2)

# 6. similar listicles may corroborate, but the gate still drops them
lst = [_item("5 Greatest Time Travel Anime of All Time, Ranked", "CBR", "entertainment"),
       _item("5 Best Time Travel Anime of All Time, Ranked", "ScreenRant", "entertainment")]
check("listicle pair never breaks", pick_breaking(score_items(lst), CFG) == [])

# 7. AI category gate: lifestyle/mush never breaks, hard news does
check("film category never breaks",
      pick_breaking([_item("Coup attempt foiled", "BBC World", "geopolitics", True, "film")], CFG) == [])
check("other category never breaks",
      pick_breaking([_item("Why women carry the mental load", "BBC Top", "geopolitics", True, "other")], CFG) == [])
check("politics category breaks",
      len(pick_breaking([_item("Coup attempt foiled", "BBC World", "geopolitics", True, "politics")], CFG)) == 1)
check("unknown category falls back to old rules",
      len(pick_breaking([_item("Coup attempt foiled", "BBC World", "geopolitics", True, None)], CFG)) == 1)
check("disaster category breaks",
      len(pick_breaking([_item("Earthquake hits region", "BBC World", "geopolitics", True, "disaster")], CFG)) == 1)

# 8. opinion pieces never break
check("opinion never breaks",
      pick_breaking([_item("Pay politicians for work done, writes Namiti", "dailymonitor",
                            "uganda", True, "politics")], CFG) == [])

# 9. visible-dedupe: two wires, one slot
from rank import pick_digest
dupes = [_item("President Infantino will seek re-election in March, FIFA says", "CNA",
               "geopolitics", True),
         _item("Fifa president Infantino will stand for re-election", "BBC Top",
               "geopolitics", True),
         _item("Unrelated dam project launched", "BBC World", "geopolitics", True)]
got = pick_digest(dupes, limit=3)
check("near-dupe collapsed to one slot", len(got) == 2
      and got[0]["source"] == "CNA" and got[1]["source"] == "BBC World")

# 10. sport bodies reclassify to entertainment (never breaking)
from rank import reclassify
fifa = [{"title": "President Infantino will seek re-election in March, FIFA says",
         "summary": "", "pillar": "geopolitics", "source": "CNA"}]
reclassify(fifa)
check("fifa story is entertainment", fifa[0]["pillar"] == "entertainment"
      and pick_breaking([{**fifa[0], "link": "http://f", "_score": 9,
                          "_corroborated": True, "ts": 9999999999}], CFG) == [])

# 11. corroboration partners share one digest slot (no triple lineups)
from rank import pick_digest
lineups = [
    _item("Arsenal vs Chelsea: Line-ups confirmed for London derby", "A"),
    _item("See Arsenal's starting line-up v Chelsea", "B"),
    _item("Unrelated dam project launched", "C"),
]
scored_l = score_items(lineups)
dup_links = [s["link"] for s in scored_l if s.get("_dup_of")]
check("lineup pair corroborated", len(dup_links) >= 1)
got_l = pick_digest(scored_l, limit=3)
arsenal = [g for g in got_l if "arsenal" in g["title"].lower()]
check("one slot per event", len(arsenal) == 1 and len(got_l) == 2)

print(f"{'ALL BREAKING TESTS PASSED' if not fails else f'{fails} FAILURES'}")
sys.exit(1 if fails else 0)
