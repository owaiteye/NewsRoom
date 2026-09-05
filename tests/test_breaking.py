"""Breaking-gate regression tests. Run: python tests/test_breaking.py
An anime listicle must NEVER break, even when corroborated.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rank import score_items, pick_breaking, _is_evergreen

CFG = {"breaking_whitelist": ["BBC World", "BellumActaNews"],
       "breaking_keywords": ["breaking", "urgent", "coup", "explosion", "earthquake"]}

def _item(title, source, pillar="geopolitics", corroborated=False):
    return {"title": title, "summary": "", "link": f"https://x/{abs(hash(title)) % 99999}",
            "source": source, "outlet": source, "pillar": pillar, "trust": 3,
            "ts": 9999999999, "_score": 5,
            **({"_corroborated": True} if corroborated else {})}

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

print(f"{'ALL BREAKING TESTS PASSED' if not fails else f'{fails} FAILURES'}")
sys.exit(1 if fails else 0)
