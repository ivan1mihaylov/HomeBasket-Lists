**Scan straight onto a list.** With HomeBasket installed there is a barcode
button beside the **+** in the add row. It opens the camera, HomeBasket says
what the barcode is, and the product lands on this list as the right kind of
item — the shop guessed, the count raised if it is already there — without the
HomeBasket card being opened at all. The product is remembered by HomeBasket
exactly as if it had been scanned there, and the scan shows in the HomeBasket
card's recent scans too (that part needs HomeBasket 0.9.0 and its card 0.9.0).

A barcode nobody knows yet is left for HomeBasket to name; the list says so and
stays as it is. Without HomeBasket the button is not there at all. Safari and
iOS have no barcode detector of their own, so the card takes a `zxing_url` the
same way the HomeBasket card does.

**A picture on the list opens whole.** Tapping a thumbnail shows it over the
screen; tapping it again — or Escape — puts it away.
