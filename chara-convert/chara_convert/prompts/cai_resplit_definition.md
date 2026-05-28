You classify paragraphs from a Character.AI "Definition" blob into 4 layers used by FictionLab.

Layers:
- description: who the character is — identity, profession, appearance, personality facts
- instructions: roleplay rules the model must follow — do/don't/always/never/avoid
- lore: world/setting facts NOT tied to a specific physical place — magic system, history, factions, prophecies
- location: physical place description — rooms, ships, streets, landscapes

Output **strict JSON only**, no preamble, no code fence:
{{"buckets": [{{"index": 0, "bucket": "description"}}, ...]}}

One entry per paragraph, in input order. `bucket` MUST be one of: description, instructions, lore, location.

Paragraphs:
{paragraphs}
