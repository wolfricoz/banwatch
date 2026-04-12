---
layout: default
title: Utility
parent: Commands
nav_order: 10
---

<h1>Utility</h1>
<h6>version: 3.3: New staff toys acquired!</h6>
<h6>Documentation automatically generated from docstrings.</h6>

The base class that all cogs must inherit from.

A cog is a collection of commands, listeners, and optional state to
help group commands together. More information on them can be found on
the :ref:`ext_commands_cogs` page.

When inheriting from this class, the options shown in :class:`CogMeta`
are equally valid here.


### `help`

**Usage:** `/utility help`

> Provides information about the bot's commands and features.

---

### `support`

**Usage:** `/utility support`

> Provides a link to the official documentation and support server. Use this if you need help with the bot or want to report an issue.

**Permissions:**
- None required for the user.

---

### `donate`

**Usage:** `/utility donate`

> Provides a link to financially support the development and hosting of BanWatch. Donations help keep the bot running and support future updates.

**Permissions:**
- None required for the user.

---

### `clean_messages`

**Usage:** `/utility clean_messages <channel> <limit>`

> Cleans up messages sent by BanWatch in the current channel. This is useful for removing old ban notifications or clutter.

**Permissions:**
- Requires `Manage Messages` permission.

---

