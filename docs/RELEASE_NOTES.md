Two things reported from a real list, both fixed.

### Ticking an item off said "Unknown error"

The handler read its field names from the WebSocket schema, whose keys are
voluptuous markers rather than strings, and Python refuses those as keyword
arguments. Every update raised before it got anywhere. The fields are declared
by name now, with the schema built from them, so the two cannot drift apart.

### Deleting an item did nothing

The item was deleted and then immediately put back. A sync pass reads the
linked lists before it writes to them, and an item the linked list still held
but we no longer had looked like something new to adopt — so the deletion was
undone before it could be carried across.

Only an item that is genuinely new to a linked list is adopted now. One that
was there last time and is gone from ours is one we deleted, and the push
removes it from the linked list.

### Also

The sync engine now has a test that runs without Home Assistant —
`python3 tests/test_sync.py` — walking an item through adding, ticking and
deleting from both sides. Both bugs above would have been caught by it.
