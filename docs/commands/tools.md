---
layout: default
title: Tools
parent: Commands
nav_order: 8
---

<h1>Tools</h1>
<h6>version: 3.2</h6>
<h6>Documentation automatically generated from docstrings.</h6>

The base class that all cogs must inherit from.

A cog is a collection of commands, listeners, and optional state to
help group commands together. More information on them can be found on
the :ref:`ext_commands_cogs` page.

When inheriting from this class, the options shown in :class:`CogMeta`
are equally valid here.


### `ban`

**Usage:** `/tools ban <user> <ban_type> <inform> <clean>`

> Bans a specified user from the server. This command offers options for silent bans, message cleaning, and whether to notify the user. A reason for the ban will be requested.

**Permissions:**
- Requires `Ban Members` permission.

---

### `mass_ban`

**Usage:** `/tools mass_ban <users> <ban_type> <inform> <clean>`

> Bans multiple users from the server simultaneously. This is an efficient tool for handling raids or removing multiple disruptive users at once. A single reason will apply to all.

**Permissions:**
- Requires `Ban Members` permission.

---

### `unban`

**Usage:** `/tools unban <user>`

> Revokes a ban for a specified user, allowing them to rejoin the server. This is essential for correcting banning mistakes or allowing users to return after an appeal.

**Permissions:**
- Requires `Ban Members` permission.

---

### `mass_unban`

**Usage:** `/tools mass_unban <users>`

> Revokes bans for multiple users simultaneously. This is useful for processing multiple successful appeals at once or reversing a mass ban action.

**Permissions:**
- Requires `Ban Members` permission.

---

### `reban`

**Usage:** `/tools reban <user> <ban_type> <reason>`

> Updates a user's ban reason by unbanning and immediately re-banning them with a new reason. This is useful for correcting or updating ban records without requiring the user to be present.

**Permissions:**
- Requires `Ban Members` permission.

---

### `kick`

**Usage:** `/tools kick <user> <reinvite>`

> Removes a user from the server. Unlike a ban, a kicked user can rejoin immediately if they have a valid invite. This is a less severe moderation action.

**Permissions:**
- Requires `Kick Members` permission.

---

### `export_bans`

**Usage:** `/tools export_bans`

> Fetches the entire ban list for the server and compiles it into a text file. This is extremely useful for auditing, backup, or migrating bans to another server or bot.

**Permissions:**
- Requires `Ban Members` permission.

---

### `search_bans`

**Usage:** `/tools search_bans <word> <hide>`

> Searches the server's ban database for entries containing a specific word or phrase in the reason. This helps moderators find patterns or locate specific cases quickly.

**Permissions:**
- Requires `Ban Members` permission.

---

### `copy_bans`

**Usage:** `/tools copy_bans <guild>`

> Copies all bans from a specified source server to the current server. This is designed for server owners to synchronize ban lists between servers they manage.

**Permissions:**
- Requires `Ban Members` permission.
- User must be the owner of both servers.

---

