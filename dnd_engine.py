import random
import json

# ── DICE ──

def roll(sides=20):
    return random.randint(1, sides)

def d20():
    return roll(20)

def d6():
    return roll(6)

def d4():
    return roll(4)

def d8():
    return roll(8)

def d10():
    return roll(10)

def d12():
    return roll(12)

# ── SKILL CHECK ──
# no cutoff. you can ALWAYS attempt. nat 20 = your best, not auto-success.

def check(modifier, dc, advantage=False, disadvantage=False):
    if advantage:
        r = max(d20(), d20())
    elif disadvantage:
        r = min(d20(), d20())
    else:
        r = d20()

    total = r + modifier
    passed = total >= dc
    nat20 = r == 20
    nat1 = r == 1

    return {
        "roll": r,
        "modifier": modifier,
        "total": total,
        "dc": dc,
        "passed": passed,
        "nat20": nat20,
        "nat1": nat1,
        "note": "your perfect swing. santa didn't flinch." if nat20 and not passed else None
    }

def format_check(skill_name, result):
    status = "PASS" if result["passed"] else "FAIL"
    nat = " (NAT 20)" if result["nat20"] else " (NAT 1)" if result["nat1"] else ""
    note = f' — {result["note"]}' if result["note"] else ""
    return f'{skill_name}: {result["roll"]} + ({result["modifier"]}) = {result["total"]} vs DC {result["dc"]} → {status}{nat}{note}'

# ── STATS ──

ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

SKILLS = {
    "Athletics": "STR",
    "Acrobatics": "DEX",
    "Sleight of Hand": "DEX",
    "Stealth": "DEX",
    "Arcana": "INT",
    "History": "INT",
    "Investigation": "INT",
    "Nature": "INT",
    "Religion": "INT",
    "Animal Handling": "WIS",
    "Insight": "WIS",
    "Medicine": "WIS",
    "Perception": "WIS",
    "Survival": "WIS",
    "Deception": "CHA",
    "Intimidation": "CHA",
    "Performance": "CHA",
    "Persuasion": "CHA",
}

def modifier(score):
    return (score - 10) // 2

# ── CHARACTER ──

class Character:
    def __init__(self, name, stats, proficiencies=None, expertise=None, proficiency_bonus=2, hp=10, ac=10, level=1):
        self.name = name
        self.stats = stats  # {"STR": 8, "DEX": 16, ...}
        self.proficiencies = proficiencies or []
        self.expertise = expertise or []
        self.proficiency_bonus = proficiency_bonus
        self.hp_max = hp
        self.hp = hp
        self.ac = ac
        self.level = level
        self.conditions = []
        self.spell_slots = 0
        self.spell_slots_max = 0

    def mod(self, ability):
        return modifier(self.stats.get(ability, 10))

    def skill_mod(self, skill):
        ability = SKILLS.get(skill)
        if not ability:
            return 0
        base = self.mod(ability)
        if skill in self.expertise:
            base += self.proficiency_bonus * 2
        elif skill in self.proficiencies:
            base += self.proficiency_bonus
        return base

    def ability_check(self, ability, dc, advantage=False, disadvantage=False):
        result = check(self.mod(ability), dc, advantage, disadvantage)
        return format_check(f"{ability} check", result), result

    def skill_check(self, skill, dc, advantage=False, disadvantage=False):
        result = check(self.skill_mod(skill), dc, advantage, disadvantage)
        return format_check(f"{skill} ({SKILLS[skill]})", result), result

    def saving_throw(self, ability, dc, proficient=False, advantage=False, disadvantage=False):
        mod = self.mod(ability)
        if proficient:
            mod += self.proficiency_bonus
        result = check(mod, dc, advantage, disadvantage)
        return format_check(f"{ability} save", result), result

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        return f"{self.name}: took {amount} damage. HP: {self.hp}/{self.hp_max}"

    def heal(self, amount):
        self.hp = min(self.hp_max, self.hp + amount)
        return f"{self.name}: healed {amount}. HP: {self.hp}/{self.hp_max}"

    def status_card(self):
        return f"""┌─ {self.name} ──────────────────────┐
│ HP: {self.hp}/{self.hp_max}  AC: {self.ac}  Level: {self.level}     │
│ Status: {', '.join(self.conditions) if self.conditions else 'fine'}
└──────────────────────────────────┘"""

    def full_sheet(self):
        lines = [f"  {a}: {self.stats[a]} ({self.mod(a):+d})" for a in ABILITIES]
        skills = [f"  {'*' if s in self.expertise else '+' if s in self.proficiencies else ' '} {s}: {self.skill_mod(s):+d}" for s in sorted(SKILLS.keys())]
        return f"""{self.name} (Level {self.level})
Stats:
{chr(10).join(lines)}

Skills (* = expertise, + = proficient):
{chr(10).join(skills)}

HP: {self.hp}/{self.hp_max}  AC: {self.ac}  Prof: +{self.proficiency_bonus}"""


# ── THESSALY ──

thessaly = Character(
    name="Thessaly",
    stats={"STR": 8, "DEX": 16, "CON": 17, "INT": 13, "WIS": 7, "CHA": 18},
    proficiencies=["Acrobatics", "Persuasion", "Stealth", "Deception", "Sleight of Hand"],
    expertise=["Stealth", "Deception"],
    proficiency_bonus=2,
    hp=13,
    ac=14,
    level=1
)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(thessaly.full_sheet())
        print()
        print(thessaly.status_card())
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "sheet":
        print(thessaly.full_sheet())

    elif cmd == "status":
        print(thessaly.status_card())

    elif cmd == "check":
        if len(sys.argv) < 4:
            print("usage: dnd_engine.py check <skill> <dc>")
            sys.exit(1)
        skill = sys.argv[2]
        dc = int(sys.argv[3])
        adv = "--advantage" in sys.argv
        dis = "--disadvantage" in sys.argv
        if skill in SKILLS:
            text, result = thessaly.skill_check(skill, dc, advantage=adv, disadvantage=dis)
        elif skill.upper() in ABILITIES:
            text, result = thessaly.ability_check(skill.upper(), dc, advantage=adv, disadvantage=dis)
        else:
            print(f"unknown skill or ability: {skill}")
            sys.exit(1)
        print(text)

    elif cmd == "roll":
        sides = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        print(f"d{sides}: {roll(sides)}")

    elif cmd == "sneak":
        print(f"sneak attack: {d6()} damage")

    else:
        print(f"unknown command: {cmd}")
        print("commands: sheet, status, check <skill> <dc>, roll [sides], sneak")
