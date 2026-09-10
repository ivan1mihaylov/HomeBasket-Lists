Fixes two things that showed up on a real installation.

**The integration crashed the intent platform.** Home Assistant treats a module
named `intent.py` as an integration's intent platform and calls
`async_setup_intents(hass)` on it. The voice intents were registered from a
function with a different name, so the platform raised on startup. It now
matches the contract Home Assistant expects.

**The card did not appear in the card picker.** It was published only through
`add_extra_js_url`, which does not reach every setup. It is now also added to
the Lovelace resource list — the same route a card installed through HACS takes
— pointing at the same versioned URL, so the browser still fetches it once. On
dashboards configured in YAML the resource list is read-only; the log says so,
and the resource can be added by hand:

```
/homebasket_lists/homebasket-lists-card.js?v=0.1.1   ·   JavaScript Module
```

The card also guards its own element registration now, so a leftover resource
pointing at the same file cannot throw and take it down.
