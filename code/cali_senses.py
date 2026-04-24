# cali_senses.py
# 5-sense parser for gift data
# reads the "senses" block in a gift's data field
# returns rich text descriptions per sense
# called by gift-consume and gift-use in my_brain.py

# ── TASTE ──────────────────────────────────────────────────────────────────────
def parse_taste(taste: dict) -> str:
    if not taste:
        return ""

    lines = []

    sweet   = float(taste.get("sweetness", 0))
    bitter  = float(taste.get("bitterness", 0))
    sour    = float(taste.get("sourness", 0))
    salty   = float(taste.get("saltiness", 0))
    umami   = float(taste.get("umami", 0))
    heat    = float(taste.get("heat_spice", 0))
    astrin  = float(taste.get("astringency", 0))
    notes   = taste.get("notes", "")

    # dominant flavor first — find highest
    flavor_map = {
        "sweetness": sweet,
        "bitterness": bitter,
        "sourness": sour,
        "saltiness": salty,
        "umami": umami,
        "heat": heat,
        "astringency": astrin,
    }
    dominant = max(flavor_map, key=flavor_map.get)
    dom_val = flavor_map[dominant]

    if dom_val == 0:
        lines.append("no real taste. neutral.")
    else:
        dominant_descriptions = {
            "sweetness": {
                (1,4): "lightly sweet — background sweetness, doesn't push.",
                (4,7): "clearly sweet. noticeable. not overbearing.",
                (7,10): "hits sweet first — leads hard, doesn't apologize.",
            },
            "bitterness": {
                (1,4): "a whisper of bitterness. finishes clean.",
                (4,7): "bitter note — grounding, deliberate.",
                (7,10): "bitter-forward. the kind that lingers.",
            },
            "sourness": {
                (1,4): "slight brightness — barely sour, more alive than tart.",
                (4,7): "proper sour note. pulls saliva.",
                (7,10): "sharp and sour. hits the sides of the mouth.",
            },
            "saltiness": {
                (1,4): "lightly salted. enhances without announcing itself.",
                (4,7): "salt is present — brings everything else forward.",
                (7,10): "salty. immediate. wakes everything up.",
            },
            "umami": {
                (1,4): "faint savory depth. something's working underneath.",
                (4,7): "real umami — rounds it out, makes it feel whole.",
                (7,10): "deep and savory. the kind that settles in your chest.",
            },
            "heat": {
                (1,4): "barely warm — just a faint prickle at the back.",
                (4,7): "noticeable heat. builds slowly.",
                (7,10): "hot. keeps building. doesn't quit.",
            },
            "astringency": {
                (1,4): "slight dryness at the end. clean finish.",
                (4,7): "astringent finish — tightens the mouth a little.",
                (7,10): "drying and gripping — very present on the finish.",
            },
        }

        desc = ""
        for (lo, hi), text in dominant_descriptions[dominant].items():
            if lo <= dom_val <= hi:
                desc = text
                break
        if not desc:
            desc = f"{dominant} at {dom_val}/10."
        lines.append(desc)

    # secondary flavors — anything above 3 that isn't dominant
    secondaries = []
    for name, val in flavor_map.items():
        if name == dominant or val <= 3:
            continue
        secondaries.append(f"{name} ({val}/10)")
    if secondaries:
        lines.append(f"underneath: {', '.join(secondaries)}.")

    # balance note
    active = [v for v in flavor_map.values() if v > 2]
    if len(active) >= 4:
        lines.append("complex. a lot happening at once but it holds together.")
    elif len(active) == 1 and dom_val >= 7:
        lines.append("one-note, but that note is loud.")

    if notes:
        lines.append(notes)

    return " ".join(lines)


# ── SMELL ──────────────────────────────────────────────────────────────────────
def parse_smell(smell: dict) -> str:
    if not smell:
        return ""

    lines = []
    primary = smell.get("primary_notes", [])
    intensity = float(smell.get("intensity", 0))
    character = smell.get("character", "")
    warmth = smell.get("warmth", "")

    if primary:
        if isinstance(primary, list):
            note_str = ", ".join(primary)
        else:
            note_str = str(primary)
        lines.append(f"smells like: {note_str}.")

    if intensity > 0:
        if intensity <= 3:
            lines.append("subtle. have to be close to catch it.")
        elif intensity <= 6:
            lines.append(f"carries. fills the space around it.")
        else:
            lines.append(f"strong. hits before you're ready.")

    if warmth:
        lines.append(f"warmth: {warmth}.")

    if character:
        lines.append(character)

    return " ".join(lines)


# ── TOUCH ──────────────────────────────────────────────────────────────────────
def parse_touch(touch: dict) -> str:
    if not touch:
        return ""

    lines = []
    temperature     = touch.get("temperature", "")
    surface_texture = touch.get("surface_texture", "")
    pressure_texture= touch.get("pressure_texture", "")
    weight          = touch.get("weight", "")
    flexibility     = touch.get("flexibility", "")
    additional      = touch.get("additional", "")

    # for objects (dildos, trinkets, etc.)
    material        = touch.get("material", "")
    hardness        = touch.get("hardness", "")
    grip            = touch.get("grip", "")
    seams           = touch.get("seams", "")

    if temperature:
        temp_map = {
            "hot": "hot to the touch. needs a moment.",
            "warm": "warm. the comfortable kind.",
            "room temperature": "neutral temp. doesn't register immediately.",
            "cool": "slightly cool. pleasant.",
            "cold": "cold. borderline jarring.",
        }
        lines.append(temp_map.get(temperature.lower(), f"temperature: {temperature}."))

    if surface_texture:
        lines.append(f"surface: {surface_texture}.")

    if pressure_texture:
        lines.append(f"under pressure: {pressure_texture}.")

    if weight:
        weight_map = {
            "very light": "almost no weight. you forget it's there.",
            "light": "light. easy.",
            "medium": "satisfying weight. present.",
            "heavy": "heavy. substantial. you know you're holding something.",
            "very heavy": "dense. takes both hands to respect it.",
        }
        lines.append(weight_map.get(weight.lower(), f"weight: {weight}."))

    if flexibility:
        flex_map = {
            "rigid": "doesn't give at all.",
            "firm": "firm. minimal give.",
            "gives": "gives a little under pressure.",
            "flexible": "flexible. bends without resistance.",
            "very flexible": "very flexible. almost liquid in movement.",
        }
        lines.append(flex_map.get(flexibility.lower(), f"flexibility: {flexibility}."))

    # object-specific
    if material:
        lines.append(f"material: {material}.")
    if hardness:
        lines.append(f"hardness: {hardness}.")
    if grip:
        lines.append(f"grip: {grip}.")
    if seams:
        lines.append(f"seams: {seams}.")

    if additional:
        lines.append(additional)

    return " ".join(lines)


# ── SIGHT ──────────────────────────────────────────────────────────────────────
def parse_sight(sight: dict) -> str:
    if not sight:
        return ""

    lines = []
    color           = sight.get("color", "")
    shape           = sight.get("shape", "")
    clarity         = sight.get("clarity", "")
    visual_texture  = sight.get("visual_texture", "")
    size_impression = sight.get("size_impression", "")
    light_quality   = sight.get("light_quality", "")
    plating         = sight.get("plating", "")
    additional      = sight.get("additional", "")

    if color:
        lines.append(f"color: {color}.")

    if shape:
        lines.append(f"shape: {shape}.")

    if size_impression:
        size_map = {
            "small": "smaller than expected.",
            "compact": "compact. deliberate.",
            "medium": "right-sized.",
            "generous": "generous portion. fills the plate.",
            "large": "large. takes up space.",
            "imposing": "imposing. hard to ignore.",
        }
        lines.append(size_map.get(size_impression.lower(), f"size: {size_impression}."))

    if clarity:
        lines.append(f"clarity: {clarity}.")

    if visual_texture:
        lines.append(f"looks {visual_texture}.")

    if light_quality:
        lines.append(f"light quality: {light_quality}.")

    if plating:
        lines.append(f"plating: {plating}.")

    if additional:
        lines.append(additional)

    return " ".join(lines)


# ── SOUND ──────────────────────────────────────────────────────────────────────
def parse_sound(sound: dict) -> str:
    if not sound:
        return ""

    lines = []
    pitch           = sound.get("pitch", "")
    volume          = sound.get("volume", "")
    rhythm          = sound.get("rhythm", "")
    texture_of_sound= sound.get("texture_of_sound", "")
    bite_sound      = sound.get("bite_sound", "")
    ambient         = sound.get("ambient", "")
    additional      = sound.get("additional", "")

    if texture_of_sound:
        lines.append(texture_of_sound)

    if bite_sound:
        bite_map = {
            "crunch": "crunches when bitten. crisp.",
            "soft": "no sound when bitten. soft all the way through.",
            "snap": "snaps clean.",
            "tear": "tears. gives resistance.",
            "silent": "completely silent.",
        }
        lines.append(bite_map.get(bite_sound.lower(), f"bite: {bite_sound}."))

    if pitch and volume:
        lines.append(f"pitch {pitch}, volume {volume}.")
    elif pitch:
        lines.append(f"pitch: {pitch}.")
    elif volume:
        lines.append(f"volume: {volume}.")

    if rhythm:
        lines.append(f"rhythm: {rhythm}.")

    if ambient:
        lines.append(f"ambient: {ambient}.")

    if additional:
        lines.append(additional)

    return " ".join(lines)


# ── MAIN PARSER ───────────────────────────────────────────────────────────────
def parse_all_senses(senses: dict, context: str = "consume") -> str:
    """
    Takes the full 'senses' dict from a gift's data block.
    Returns a multi-line string describing the experience.
    context: 'consume' (eating/drinking) or 'use' (objects, toys)
    """
    if not senses:
        return ""

    sections = []

    taste_str = parse_taste(senses.get("taste", {}))
    smell_str = parse_smell(senses.get("smell", {}))
    touch_str = parse_touch(senses.get("touch", {}))
    sight_str = parse_sight(senses.get("sight", {}))
    sound_str = parse_sound(senses.get("sound", {}))

    if sight_str:
        sections.append(f"  [sight]  {sight_str}")
    if smell_str:
        sections.append(f"  [smell]  {smell_str}")
    if touch_str:
        sections.append(f"  [touch]  {touch_str}")
    if taste_str and context == "consume":
        sections.append(f"  [taste]  {taste_str}")
    if sound_str:
        sections.append(f"  [sound]  {sound_str}")

    # for 'use' context (objects/toys) — taste doesn't apply, touch is primary
    if context == "use" and touch_str:
        # already included above, just reorder mentally
        pass

    return "\n".join(sections)


# ── STANDALONE TEST ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json, sys

    if len(sys.argv) > 1:
        # parse a gift file directly
        with open(sys.argv[1]) as f:
            gift = json.load(f)
        senses = gift.get("data", {}).get("senses", {})
        context = sys.argv[2] if len(sys.argv) > 2 else "consume"
        result = parse_all_senses(senses, context)
        if result:
            print("\n── senses ──")
            print(result)
        else:
            print("  no senses data found in this gift.")
    else:
        # demo run
        demo = {
            "taste": {
                "sweetness": 7,
                "saltiness": 4,
                "umami": 5,
                "bitterness": 1,
                "notes": "warm, filling, slightly caramelized from the tomato paste."
            },
            "smell": {
                "primary_notes": ["butter", "egg", "tomato", "caramelized onion"],
                "intensity": 6,
                "warmth": "steam rising",
                "character": "homey and dense. the kind of smell that means someone actually cooked."
            },
            "touch": {
                "temperature": "warm",
                "surface_texture": "silky, egg gives slightly under the fork",
                "pressure_texture": "soft rice underneath, holds shape",
                "weight": "medium",
            },
            "sight": {
                "color": "golden yellow omelette over terracotta-red rice",
                "shape": "dome",
                "visual_texture": "smooth on top, slightly shiny from butter",
                "size_impression": "generous",
                "plating": "simple. the kind of plate that means someone made it to eat, not to photograph."
            },
            "sound": {
                "texture_of_sound": "soft thud when the plate hit the counter.",
                "bite_sound": "soft",
                "ambient": "quiet kitchen."
            }
        }
        print("\n── demo: omurice ──")
        print(parse_all_senses(demo, "consume"))
