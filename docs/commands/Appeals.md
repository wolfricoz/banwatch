---
layout: default
title: Appeals
parent: Commands
nav_order: 1
---

<h1>Appeals</h1>
<h6>version: 3.2</h6>
<h6>Documentation automatically generated from docstrings.</h6>

Commands for users to appeal their bans or report unjust bans.


### `create`

**Usage:** `/appeals create <guild>`

> Submit an appeal for a ban from a specific server. You can't appeal if:
- The server does not allow appeals.
- You have already appealed to that server.
- You are blacklisted from using the bot.
- The ban is hidden

**Permissions:**
- No special permissions are needed. This command can be used by anyone to appeal their own bans.

---

### `report`

**Usage:** `/appeals report <guild>`

> Report a ban that you believe to be unjust or harmful to Banwatch staff for further investigation. You can't report if:
- The server allows appeals and you have not appealed yet.
- You are blacklisted from using the bot.
- The ban is hidden.

---

