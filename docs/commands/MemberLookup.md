---
layout: default
title: MemberLookup
parent: Commands
nav_order: 4
---

<h1>MemberLookup</h1>
<h6>version: 3.2</h6>
<h6>Documentation automatically generated from docstrings.</h6>

Commands to look up users and check for bans across all monitored servers.


### `lookup`

**Usage:** `/memberlookup lookup <user> <ban_id> <override>`

> Looks up a user's ban history across all monitored servers.
Can search by user or a specific ban ID.

**Permissions:**
- `Ban Members`

---

### `checkall`

**Usage:** `/memberlookup checkall`

> Scans all members in the current server against the global ban database.
Reports users who are found in the database.

**Permissions:**
- `Ban Members`

---

