---
layout: default
title: Config
parent: Commands
nav_order: 2
---

<h1>Config</h1>
<h6>version: 3.2</h6>
<h6>Documentation automatically generated from docstrings.</h6>

Configure Banwatch for your server. Set channels, toggle features, and check permissions.


### `help`

**Usage:** `/config help`

> If you're feeling stuck or need assistance with configuring the bot, this command will provide you with helpful information and guidance.

---

### `change`

**Usage:** `/config change <option> <channel>`

> Changes server-specific settings for Banwatch.

**Permissions:**
- `Manage Server`

---

### `appeals`

**Usage:** `/config appeals <allow>`

> Enables or disables the ban appeal system for this server.

**Permissions:**
- `Manage Server`

---

### `visibility`

**Usage:** `/config visibility <hide>`

> Toggles whether this server's bans are visible in public lookups.

**Permissions:**
- `Manage Server`

---

### `permissioncheck`

**Usage:** `/config permissioncheck`

> Checks if the bot has the required permissions in the current channel and server. This is the first step in troubleshooting if the bot is not functioning as expected. Please run this command before contacting support.

**Permissions:**
- None required for the user.

---

