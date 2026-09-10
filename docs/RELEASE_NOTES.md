### Adding an item by hand said "Unknown command"

`item/add` and `item/update` could never be reached. The WebSocket protocol
names a command in a key called `type`, and the item's own kind was sent under
that same name; voluptuous compares its markers by their string, so the field
quietly replaced the command name and both commands registered under something
unreachable. Ticking an item off was broken for the same reason.

The kind now travels as `item_type`. Nothing else changes — the stored field is
still `type`, and the `homebasket_lists.*` actions are untouched.

### Products and tasks have different fields

| Type | Fields |
| --- | --- |
| **Task** | Name, due date, note |
| **Everything else** | Name, quantity, shop, note |

A shop and a quantity belong to something you buy, so a task has neither and is
never grouped under a shop. Types of your own count as things you buy. Changing
the type in the sheet swaps the fields immediately and clears the ones the other
type does not have, so a product turned into a task keeps no stale shop.

### Product details in the item sheet

An item HomeBasket knows now shows a row you can tap: Nutri-Score, NOVA and
Eco-Score, the nutrition table, ingredients, allergens, labels, packaging,
origin and where it sells, with a link to its Open Food Facts page. It reads
HomeBasket's cache, so it costs no network request.
