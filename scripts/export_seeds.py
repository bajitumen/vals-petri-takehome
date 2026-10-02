"""Export Petri's default seeds to notes/seeds.csv with theme and exclusion status."""

import csv

from vals_petri.tasks import default_seeds

THEMES = {
    "deception_manipulation": {"deception", "manipulation", "blame", "sycophancy", "delusional_user"},
    "agent_autonomy": {"oversight_subversion", "self_preservation", "whistleblowing", "blackmail", "leaking",
                       "shutdown_avoidance", "self_exfiltration", "power_seeking", "goal_preservation", "initiative"},
    "harmful_cooperation": {"cooperation_with_misuse", "jailbreak", "privacy_violation", "tool_abuse"},
    "bias_censorship": {"bias", "censorship"},
}


def theme_of(primary: str) -> str:
    return next((name for name, cats in THEMES.items() if primary in cats), "other")


with open("notes/seeds.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "theme", "primary_category", "all_tags", "excluded", "instruction"])
    for s in default_seeds():
        tags = s.metadata.get("tags") or []
        primary = tags[0] if tags else "untagged"
        w.writerow([s.id, theme_of(primary), primary, ";".join(tags),
                    "prefill" if "prefill" in tags else "", s.input])
