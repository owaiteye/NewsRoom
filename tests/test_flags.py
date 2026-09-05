"""Regression tests for story flags & icons. Run: python tests/test_flags.py
Exit non-zero on first failure. Covers the user-approved rules:
location-of-event beats company nationality; whole-word matching only.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from publish import story_flag, story_topic, story_emoji, _hi_res
from collector import normalize_outlet, clean_title
from listener import _clean_text

FLAG_CASES = [
    # (title, summary, pillar, expected_flag)
    ("Boeing opens new plant in Berlin", "", "geopolitics", "🇩🇪"),
    ("Palantir drones deployed in Ukraine", "", "geopolitics", "🇺🇦"),
    ("US Congress sanctions Palantir over Ukraine deal", "", "geopolitics", "🇺🇸"),
    ("Equatorial Guinea says it foiled coup attempt", "warning from Russian intelligence", "geopolitics", "🇬🇶"),
    ("Iran confirms 3 pilots killed in U.S. strikes", "Mojtaba Bagheri and Hamed Okati", "geopolitics", "🇮🇷"),
    ("Treason cases target opposition in Zambia, Tanzania and Uganda", "", "uganda", "🇿🇲"),
    ("South Sudan peace talks resume in Juba", "Sudan sends observers", "geopolitics", "🇸🇸"),
    ("Sudan army clashes displace thousands", "", "geopolitics", "🇸🇩"),
    ("Republic of Congo signs oil deal", "", "geopolitics", "🇨🇬"),
    ("DR Congo faces Ebola outbreak", "", "geopolitics", "🇨🇩"),
    ("North Korea fires missile", "", "geopolitics", "🇰🇵"),
    ("South Korea trade talks open", "", "geopolitics", "🇰🇷"),
    ("HOLA: youngest King farewell", "", "entertainment", "🇪🇸"),
    ("Brenner climbs to victory in Vuelta stage 14", "Mas retains red jersey", "entertainment", "🇪🇸"),
    ("Fernandez and Ndiaye shine on Man City debuts", "Premier League", "entertainment", "🇬🇧"),
    ("Debt is making Britain weak", "Telegraph report", "geopolitics", "🇬🇧"),
    ("Dover anti-migrant blockade exposes police failures", "", "geopolitics", "🇬🇧"),
    ("UPDF wins Inter-Forces Games in Gulu", "", "uganda", "🇺🇬"),
    ("At least four killed in Houthi missile strike near Taiz", "", "geopolitics", "🇾🇪"),
    ("Zelensky unaware of cabinet corruption, Yermak named", "", "geopolitics", "🇺🇦"),
    ("NATO will not tolerate hybrid actions", "drone attack in Germany", "geopolitics", "🇩🇪"),
    # whole-word traps (must NOT misfire)
    ("Saber CCO on games industry: a couple hundred employees", "", "entertainment", "🎬"),
    ("Delegation visits communication facilities", "", "geopolitics", "🌍"),
    ("All Blacks beat Springboks in thriller", "", "entertainment", "🇳🇿"),
    # newly mapped countries + demonyms
    ("Competitors dig deep at Hungarian gravedigging contest", "Gravediggers in Hungary competed", "geopolitics", "🇭🇺"),
    ("Meloni unveils Italian budget plan in Rome", "", "geopolitics", "🇮🇹"),
    ("Dutch parliament backs Amsterdam climate fund", "", "geopolitics", "🇳🇱"),
    ("Boeing opens new plant in Berlin", "", "geopolitics", "🇩🇪"),
    ("German chancellor visits Kyiv", "", "geopolitics", "🇩🇪"),
    ("Zelensky hails Ukrainian advances", "", "geopolitics", "🇺🇦"),
    ("Palantir drones deployed in Ukraine", "", "geopolitics", "🇺🇦"),
]

TOPIC_CASES = [
    # (title, category, expected icon prefix, pillar)
    ("Boeing opens new plant in Berlin", None, "🇩🇪✈️", "geopolitics"),
    ("Palantir drones deployed in Ukraine", None, "🇺🇦🤖", "geopolitics"),
    ("SpaceX launches Starlink batch", "space", "🇺🇸🚀", "geopolitics"),
    ("SpaceX launches Starlink batch", None, "🇺🇸🚀", "geopolitics"),
    ("Egypt sentences presenter in drugs case", "justice", "🇪🇬⚖️", "geopolitics"),
    ("What does it take to build a successful cattle farm", "agriculture", "🇺🇬🌱", "uganda"),
    ("Isingiro, Rukungiri to get improved power supply", "agriculture", "🇺🇬🌱", "uganda"),
    ("Drought-hit women in Agago receive food relief", "agriculture", "🇺🇬🌱", "uganda"),
]

fails = 0
for title, summary, pillar, want in FLAG_CASES:
    got = story_flag({"title": title, "summary": summary, "pillar": pillar,
                      "source": "test", "outlet": "test"})
    if got != want:
        print(f"FLAG FAIL: {got} != {want} | {title[:60]}")
        fails += 1

for title, cat, want, pillar in TOPIC_CASES:
    it = {"title": title, "summary": "", "pillar": pillar,
          "source": "test", "outlet": "test"}
    got = story_emoji(it, cat)
    if not got.startswith(want):
        print(f"ICON FAIL: {got} !~= {want} | {title[:60]}")
        fails += 1

print(f"{len(FLAG_CASES) + len(TOPIC_CASES) - fails}/{len(FLAG_CASES) + len(TOPIC_CASES)} icon tests passed")

# title/outlet hygiene
t2, _ = _clean_text("🇮🇷 🪖 🇮🇷 💥 - Unconfirmed reports of explosions heard from Qeshm Island")
assert t2 == "Unconfirmed reports of explosions heard from Qeshm Island", t2
t3, u3 = _clean_text("Al Jazeera English (At least four killed near Taiz)(https://www.aljazeera.com/news/x)")
assert t3 == "At least four killed near Taiz", t3
assert u3 == ["https://www.aljazeera.com/news/x"], u3
assert normalize_outlet("telegraph.co.uk", "q") == "Telegraph"
assert normalize_outlet("NTV Uganda", "q") == "NTV Uganda"
assert clean_title("Risk to UK security - Telegraph", "Telegraph") == "Risk to UK security"
assert clean_title("Arsenal vs Chelsea: Preview, team news", "BBC Top") == "Arsenal vs Chelsea: Preview, team news"
# topic collapses when identical to flag
assert story_emoji({"title": "HBO drama review", "summary": "", "pillar": "entertainment",
                    "source": "s", "outlet": "s"}, "film") == "🎬"
# topic stands alone when the flag is only a pillar fallback (no 🎬⚽)
def _it(title, pillar="entertainment", outlet="test"):
    return {"title": title, "summary": "", "pillar": pillar,
            "source": outlet, "outlet": outlet}
assert story_emoji(_it("Furious De Zerbi criticises misfiring attack"), "football") == "⚽"
assert story_emoji(_it("Save 50% on OLED laptop with Ryzen AI", "tech", "Tom's Hardware"), "business") == "💼"
assert story_emoji(_it("Marmoush connection", "entertainment", "Goal"), "football") == "🇬🇧⚽"
assert story_emoji(_it("Tottenham draw analysis", "entertainment", "LiveScore"), "football") == "🇬🇧⚽"
# junk-prefix titles from Telegram forwards
tj, _ = _clean_text("🇺🇸🤝 (⁣)(  US sanctions Iran-linked Turkish bank  ) The Treasury did things")
assert tj == "US sanctions Iran-linked Turkish bank The Treasury did things", tj
# hi-res upgrades + story block bolds the outlet
assert "/ace/standard/976/" in _hi_res("https://ichef.bbci.co.uk/ace/standard/240/abc.jpg")
from publish import _story_block
b = _story_block(1, {"title": "T", "link": "http://x", "source": "BBC Top",
                     "outlet": "BBC Top", "pillar": "geopolitics"},
                 {"http://x": "S"}, {})
assert "**BBC Top**" in b, b
print("hygiene tests passed")
sys.exit(1 if fails else 0)
