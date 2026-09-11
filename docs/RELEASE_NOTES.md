**Scanning onto a list works on an iPhone now.**

Safari reads no barcodes of its own, so the scan button beside the **+** did
nothing there unless you hosted a ZXing build yourself. One is shipped with
this integration now and served from your own installation — nothing is fetched
from a CDN, and there is nothing to set up.

The fallback itself was also broken where it was configured: the card called a
method the library does not have and unwrapped its export wrongly. Both fixed.

`zxing_url` still works, for a build of your own.
