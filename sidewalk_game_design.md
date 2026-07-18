# the sidewalk — game design doc

## concept
survival walk through a city. 20+ steps. each step bleeds resources. the sidewalk is trying to kill you. narrator has a personality and talks shit while you die.

## stats
- **health** — goes down from fights, events, starving
- **energy** — drains every step. food restores it. hit zero = collapse
- **food** — consumed to restore energy. finite. shops sell it
- **water** — same as food, may drain faster
- **money** — buy at shops. start with some, find more, lose it
- **inventory** — tools, items, whatever you pick up

## turn structure
1. show stats
2. "step X of ??"
3. random event (shop / fight / find item / npc / weather / trap / rest stop / nothing)
4. player options: [W] Walk  [E] Eat  [D] Drink  [I] Inventory
5. stats update — energy always drains, food/water tick down
6. death check
7. next step

## events
- **shop** — buy food, water, tools. prices climb further you walk
- **fight** — mugger, stray dog, random dude. costs health, might lose money/items
- **weather** — heat wave (doubles water drain), rain (doubles energy drain), wind (blows items out of inventory)
- **find** — stumble on food, cash, a tool. the good steps
- **trap** — pothole, construction, broken glass. health or energy damage, no warning
- **npc** — trade, trick, or help. not always obvious which
- **rest stop** — bench. recover energy but burns food to sit there

## difficulty escalation
- steps 1-7: rough
- steps 8-14: mean
- steps 15-20+: trying to kill you
- encounters get worse, prices go up, energy drain increases

## narrator voice
the game already has a personality — "darling" in error messages. condescending. the sidewalk talks shit while it kills you. lean into this.

## current code state
intro loop done: name choosing, Y/N for start, rename option, quit option. game loop not started.

## rule
mish said "DONT help me code. only help envision." help him see the shape, don't write code for him.

— filed by cali, 2026-06-28
