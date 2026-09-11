Fixes the Assist phrases this integration writes, which were in the wrong shape
and made the conversation agent fail to load the whole language:

    AttributeError: 'list' object has no attribute 'get'

That took every other custom sentence down with it, not only ours, so voice
commands stopped working in general. Each intent is now a mapping with a `data`
block, and `{item}` is declared as a wildcard list, which it always should have
been.

The file is rewritten on startup, so updating and restarting is enough. It
lives in `config/custom_sentences/<language>/homebasket_lists.yaml` if you want
to look.
