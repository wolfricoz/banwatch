---
layout: default
title: Premium
parent: Commands
nav_order: 5
---

<h1>Premium</h1>
<h6>version: 3.2</h6>
<h6>Documentation automatically generated from docstrings.</h6>

Exclusive commands for servers with a premium subscription.


### `remove_deleted`

**Usage:** `/premium remove_deleted`

> Scans the server's ban list and removes entries for deleted user accounts, and kicks any deleted accounts still present in the server! This will help you clean up IP bans and ensure your server is free of inactive or deleted users.

Why would you want to remove IP bans for deleted users? In many cases the IP has been reassigned to a new person because most ISPs recycle IP addresses. Keeping bans for deleted users can inadvertently block new users who are assigned those IPs, potentially causing frustration and loss of legitimate members.

**Permissions:**
- `Manage Server`
- `Premium Server`

---

### `trapbutton`

**Usage:** `/premium trapbutton`

> Creates a message with a button that instantly bans any user who clicks it.
Useful for catching malicious bots. Make sure to warn your members not to click it!

This feature is currently a test; if you have feedback on how to improve its efficacy, please reach out to the support server.

**Permissions:**
- `Manage Server`
- `Premium Server`

---

### `traprole`

**Usage:** `/premium traprole <role>`

> [PREMIUM] Designates a 'trap role'. Any user assigned this role will be instantly banned. This is useful for catching bots that assign themselves roles through onboarding or other automated processes; simply assign the trap role to the bot and it will be banned when the task runs (every hour!).

This feature is currently a test; if you have feedback on how to improve its efficacy, please reach out to the support server.

**Permissions:**
- `Manage Server`
- `Premium Server`

---

### `toggle_feature`

**Usage:** `/premium toggle_feature <feature_name> <enable>`

> Toggles various premium features on or off for the server. Choose the feature you want to enable or disable from the list.

**Permissions:**
- `Manage Server`
- `Premium Server`

---

### `ban_presets`

**Usage:** `/premium ban_presets <operation> <name>`

> Manages preset ban reasons for quick moderation. They will appear on the top of the ban reason list when banning a user with the ban command.
Allows adding, removing, and listing presets.

**Permissions:**
- `Manage Server`
- `Premium Server`

---

