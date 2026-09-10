First release of HomeBasket Lists.

Shopping lists that stay in step with the built-in Home Assistant to-do lists,
and know what HomeBasket knows about each product.

### Lists

One config entry is one list, so **Add entry** makes another. A list holds what
a to-do item cannot: a shop, a quantity, a type, and a link to a HomeBasket
product. Each list gets one entity — `sensor.<list>_open_items`, counting what
is left, for badges and zone automations.

### Two-way sync

A list can mirror any number of built-in to-do lists, with ours as the hub:

```
add in a linked list      →  ours, then every other linked list
tick in a linked list     →  ours, then every other linked list
delete in a linked list   →  gone everywhere
anything in ours          →  every linked list
```

Items are matched by name, since the same item has a different uid in every
list. The first sync adopts whatever the linked lists already hold and leaves
the shop empty — a shop is something you assign afterwards.

### Voice

Three intents of its own — add, complete, read — with the sentences written into
`custom_sentences/` in Bulgarian and English:

- *добави мляко в Пазаруване* / *add milk to Shopping*
- *отметни мляко от Пазаруване* / *check off milk from Shopping*
- *какво има в Пазаруване* / *what is on Shopping*

Restart Home Assistant, or reload Assist, after adding a list: the sentences
carry the list names and are read at startup.

### Shops

A shop is a zone. `homebasket_lists.get_items` with a `store` returns what to
buy there **and** the items with no shop, since those can be bought anywhere —
which is exactly what a zone reminder needs. The README has a ready automation.

### HomeBasket products

With [HomeBasket](https://github.com/ivan1mihaylov/HomeBasket) installed, an
item whose name exactly matches a product is linked to it and the card shows its
picture and category. Only an exact match counts. HomeBasket is optional.

### The card

Comes with the integration — no second download and no Lovelace resource to add.
Groups open items by shop, shows product pictures, quantities and types, and
edits an item in place.
