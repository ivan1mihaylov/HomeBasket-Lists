### Three kinds of item, each with its own fields

An item is a product, a task, or neither:

| Type | Fields |
| --- | --- |
| **Product** | Name, quantity, shop, note |
| **Task** | Name, due date, how long it takes, tools, note |
| **None** | Name, note |

"None" is a real choice now, not an empty type: a plain line with a name and a
note, for something you just want to remember. Only a product carries a shop
and a quantity, and only a product is grouped under a shop.

### Tasks say how long they take, and what they need

**Takes** is a number with a unit — minutes, hours or days. **Tools** is free
text: a drill, a ladder, a spare filter. Both are optional, and both show on the
item's row so a glance at the list tells you what a job needs.

Switching an item's type swaps the fields immediately and clears what the new
type does not have.

### Also

The item type is no longer a per-list setting — the three kinds are fixed, so
there is nothing to configure. The `homebasket_lists.add_item` and
`update_item` actions take `due`, `duration`, `duration_unit` and `tools` as
well.
