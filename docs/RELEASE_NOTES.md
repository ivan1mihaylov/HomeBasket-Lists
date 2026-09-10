A failed product search looked exactly like a search that found nothing: the
error was caught and thrown away, so there was no way to tell "HomeBasket knows
no such product" from "the request never arrived".

It now reports. A failure is logged to the browser console, and a search that
cannot reach the integration at all — which happens when Home Assistant has not
been restarted after an update — says so once instead of staying quiet.

Nothing is asked for when HomeBasket is not installed, where there is nothing
to suggest anyway.
