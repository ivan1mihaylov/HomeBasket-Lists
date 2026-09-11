**Something already on the list counts up.** Adding a product a list already
holds raises its quantity instead of repeating the line — two bottles of milk
are *milk, 2 pcs* — wherever it comes from: a scan, the card, an action or a
voice assistant. The new **Something that is already on the list** setting
changes that to keeping the one that is there, or to writing a second line. A
task has no quantity to raise, so counting keeps the task already on the list.

**Scans land here directly.** With HomeBasket 0.7.0 or later, a scan can go
straight onto one of these lists rather than through a to-do entity; the list is
chosen in HomeBasket's settings. The API gained `async_add_item` for that, and
neither integration needs the other installed.

**Items can carry a photo.** Anything HomeBasket has no picture for — a task, a
loose vegetable, a part from the hardware shop — can have a photo of its own,
taken with the camera or picked from the gallery, shown on the item's row. It
sits at the top of the item sheet, is shrunk before it is sent, and is kept in
Home Assistant's own storage rather than on a public path. Deleting the item, or
the list, deletes the photos with it.
