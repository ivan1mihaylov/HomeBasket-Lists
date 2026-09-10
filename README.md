# HomeBasket Lists

Shopping lists for Home Assistant that stay in step with the built-in to-do
lists, and know what HomeBasket knows about each product.

<p><img src="docs/list.png" alt="The card" width="46%"></p>

Each list is a normal `todo` entity, so voice assistants, the built-in To-do
panel and every existing automation work with it exactly as they do with the
lists Home Assistant ships. The extra information — shop, quantity, type,
linked product — lives beside it and shows up in this integration's own card.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories**
2. URL `https://github.com/ivan1mihaylov/HomeBasket-Lists`, type **Integration**
3. Install, then restart Home Assistant
4. **Settings → Devices & Services → Add Integration → HomeBasket Lists**

The dashboard card comes with the integration — there is no second download and
no Lovelace resource to add. Add it to a dashboard with **Add card → HomeBasket
Lists**.

### Manual

Copy `custom_components/homebasket_lists` into `config/custom_components/` and
restart Home Assistant.

## Lists

One config entry is one list, so **Add entry** on the integration creates
another. Each list has:

| Setting | Meaning |
| --- | --- |
| **Keep in sync with** | Built-in to-do lists this one mirrors, in both directions. Any number of them. |
| **Shops** | Zones that count as shops. An item can be assigned one. |
| **Item types** | What an item can be, e.g. product or task. Add your own. |
| **Recognise HomeBasket products** | Match item names against HomeBasket, so the card can show pictures and categories. |

## How the sync works

Our list is the hub, the linked lists are spokes:

```
add in a spoke      →  the hub, then every other spoke
tick in a spoke     →  the hub, then every other spoke
delete in a spoke   →  gone everywhere
anything in the hub →  every spoke
```

Items are matched **by name**, because the same item has a different uid in
every list. Two consequences worth knowing:

- A rename looks like a delete plus an add. Renames are picked up on the
  five-minute reconcile rather than instantly, since a to-do entity's state
  does not change when an item is only renamed.
- Two items with the same name on one list are treated as one.

The first sync adopts whatever the linked lists already contain and **leaves
the shop empty** — a shop is something you assign afterwards, in the card.

`homebasket_lists.sync_now` runs a pass immediately.

## HomeBasket products

When [HomeBasket](https://github.com/ivan1mihaylov/HomeBasket) is installed,
an item whose name exactly matches a product is linked to it, and the card
shows that product's picture and category. Only an exact match counts — a near
match would attach the wrong product to the wrong item.

So the current arrangement holds: HomeBasket keeps putting scanned products on
whichever to-do list it is configured with, and this integration picks them up
from there and recognises them. HomeBasket is optional; without it, items simply
carry no product.

## Shops and reminders

A shop is a zone. Assign one to an item and it belongs to that shop; leave it
empty and the item can be bought anywhere.

`homebasket_lists.get_items` with a `store` returns what to buy there —
**including the items with no shop**, since those can be bought anywhere. That
is what a reminder automation needs:

```yaml
automation:
  - triggers:
      - trigger: zone
        entity_id: person.ivan
        zone: zone.kaufland
        event: enter
    actions:
      - action: homebasket_lists.get_items
        data:
          store: zone.kaufland
          status: needs_action
        response_variable: shopping
      - condition: template
        value_template: "{{ shopping.count > 0 }}"
      - action: notify.mobile_app_phone
        data:
          title: Kaufland
          message: >-
            {{ shopping['items'] | map(attribute='summary') | join(', ') }}
```

## Actions

| Action | What it does |
| --- | --- |
| `homebasket_lists.add_item` | Add an item with shop, type, quantity and note. |
| `homebasket_lists.update_item` | Change an item. Only the fields you pass are touched. |
| `homebasket_lists.remove_item` | Delete it here and in every linked list. |
| `homebasket_lists.get_items` | Read items, filtered by shop, type or status. |
| `homebasket_lists.sync_now` | Run a sync pass now. |

The ordinary `todo.*` actions work too, since each list is a to-do entity.

## Using it from another integration

```python
api = hass.data.get("homebasket_lists_api")
for board in api.lists:
    print(board["name"], len(board["items"]))

to_buy = api.items_for_store("zone.kaufland")
```

Listen for `homebasket_lists_updated` to know when something changed.

## The card

```yaml
type: custom:homebasket-lists-card
```

| Option | Default | Description |
| --- | --- | --- |
| `title` | the list's name | Card heading. |
| `list` | all | Name or entry id of one list. Empty shows a tab per list. |
| `language` | Home Assistant's | `bg` or `en`. |
| `group_by_store` | `true` | Group open items under their shop. |
| `show_completed` | `true` | Show what is already ticked off. |

## License

[MIT](LICENSE)
