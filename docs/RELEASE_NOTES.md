**An item is a grocery, a product or a task.** "Product" used to mean anything
you buy, which put a bulb and a yoghurt in the same box with the same fields.
Each kind now carries what it is for:

| Kind | What it has |
| --- | --- |
| **Grocery** | Quantity and unit, shop, **best before** — shown on the item's row |
| **Product** | Quantity and unit, shop, **link** to where it comes from |
| **Task** | Deadline, how long it takes, the tools it needs |

Both bought kinds keep the quantity and the shop, and both answer *what do I
need to buy*. A scan picks the kind by itself — HomeBasket 0.8.0 knows which of
its four databases knew the barcode, and what the cat eats is a grocery while a
shampoo is a product. So is an item added by name that matches a product
HomeBasket knows.

A list can allow any of the three kinds. One still fixes the whole list; two are
meaningful as well — a shopping list that takes groceries and products turns a
task into a grocery and leaves the rest alone.

**Lists made before this are migrated on the first start:** what was a product
becomes a grocery, and a list that took products takes both. Anything that was
not food is two taps to put right.
