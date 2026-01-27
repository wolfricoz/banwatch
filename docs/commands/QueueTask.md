---
layout: default
title: QueueTask
parent: Commands
nav_order: 6
---

<h1>QueueTask</h1>
<h6>version: 3.2</h6>
<h6>Documentation automatically generated from docstrings.</h6>

The base class that all cogs must inherit from.

A cog is a collection of commands, listeners, and optional state to
help group commands together. More information on them can be found on
the :ref:`ext_commands_cogs` page.

When inheriting from this class, the options shown in :class:`CogMeta`
are equally valid here.


### `queue`

**Usage:** `/queuetask queue`

> A background task helper that abstracts the loop and reconnection logic for you.

The main interface to create this is through :func:`loop`.

---

### `display_status`

**Usage:** `/queuetask display_status`

> A background task helper that abstracts the loop and reconnection logic for you.

The main interface to create this is through :func:`loop`.

---

