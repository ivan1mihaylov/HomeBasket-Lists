**The integration carries its own icon now.** The basket with the ticked-off
list travels inside the integration, in
`custom_components/homebasket_lists/brand/`, so Home Assistant shows it on the
integrations page, in the add dialog and on the device page.

Home Assistant 2026.3 and later serve brand images straight from a custom
integration and prefer them over the central brands repository, so nothing had
to be submitted anywhere. Older versions ignore the files and lose nothing.
