Two new settings per list.

**Remind me at the shop.** When someone you follow reaches one of the list's
shops and stays there long enough to be shopping rather than driving past, the
phone that reported the arrival gets a notification with what is still open for
that shop — plus everything with no shop, since that can be bought anywhere.
Leaving before the time is up cancels it, and each shop then stays quiet for a
cooldown. Whether to notify, who to follow, how long to stay, how long to stay
quiet, whether to include the items with no shop, and which service to fall
back on are all settings of the list. Every reminder also fires
`homebasket_lists_arrival`, in case an automation wants to do something else
with it.

**Kinds of item.** A list set to tasks only makes everything on it a task, and
one set to products only makes everything a product — whether it came from the
card, an action, a voice assistant or a linked to-do list. Changing the setting
converts what is already on the list, and the card stops showing the kind
field, since there is nothing left to choose.
