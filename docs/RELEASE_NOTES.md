Aimed at working out why suggestions stay empty, which turned out to be hard to
diagnose from a phone.

**A failed search now says so on screen.** The console warning added in 0.4.2 is
no use in the Companion app, which has no console. A search that fails now shows
the reason once, and one that cannot reach the integration at all — what an
update without a restart looks like — says exactly that.

**The card's version is in its own editor**, at the bottom, so you can tell
which build the app is actually running without a console. The Companion app
keeps its own cache, separate from any browser, so it can be a version behind
everything else.

**An answer is no longer thrown away when the field changes underneath it.** The
check that dropped a stale reply compared the field's text, which a phone
keyboard can rewrite after the request has gone out — losing a good answer.
Requests are numbered now, and the newest one wins.
