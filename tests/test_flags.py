"""Regression tests for story flags & icons. Run: python tests/test_flags.py
Exit non-zero on first failure. Covers the user-approved rules:
location-of-event beats company nationality; whole-word matching only.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from publish import story_flag, story_topic, story_emoji

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
]

TOPIC_CASES = [
    # (title, category, expected_topic_or_flag_prefix)
    ("Boeing opens new plant in Berlin", None, "🇩🇪✈️"),
    ("Palantir drones deployed in Ukraine", None, "🇺🇦🤖"),
    ("SpaceX launches Starlink batch", "space", "🇺🇸🚀"),
    ("SpaceX launches Starlink batch", None, "🇺🇸🚀"),
    ("Egypt sentences presenter in drugs case", "justice", "🇪🇬⚖️"),
]

fails = 0
for title, summary, pillar, want in FLAG_CASES:
    got = story_flag({"title": title, "summary": summary, "pillar": pillar,
                      "source": "test", "outlet": "test"})
    if got != want:
        print(f"FLAG FAIL: {got} != {want} | {title[:60]}")
        fails += 1

for title, cat, want in TOPIC_CASES:
    it = {"title": title, "summary": "", "pillar": "geopolitics",
          "source": "test", "outlet": "test"}
    got = story_emoji(it, cat)
    if not got.startswith(want):
        print(f"ICON FAIL: {got} !~= {want} | {title[:60]}")
        fails += 1

print(f"{len(FLAG_CASES) + len(TOPIC_CASES) - fails}/{len(FLAG_CASES) + len(TOPIC_CASES)} icon tests passed")
sys.exit(1 if fails else 0)
