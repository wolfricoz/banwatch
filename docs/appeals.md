---
layout: default
title: Appeals
nav_order: 6
---
<div style="text-align: center">
  <h1>Appeals</h1>
  <h6>This page will explain how appeals work!</h6>
</div>
Version: 3.2


## How do appeals work?
Users get one appeal to a server by doing the command `/appeal create`, after they have filled out the modal which pops up, the server will receive a message with two buttons where they can decide to unban the user, or keep him banned.

Once that decision is made, they can not appeal again unless they are banned again with /reban, or you accept their appeal. 

If a user is abusing the appeals system, please open a ticket in the support server; abuse of this system will result in blacklisting from Banwatch.

## For servers: turning appeals on or off

Appeals are a per-server choice. Enable or disable them with:

```
/config appeals
```

When appeals are off, banned users simply can't submit one to your server.

## What a banned user sees

1. The user runs `/appeal create` for the server that banned them.
2. A short form pops up where they explain why the ban should be reconsidered.
3. Their appeal is sent to the server's staff with two buttons: **unban** or
   **keep banned**.
4. They get one appeal per ban. Until staff respond, the appeal sits as
   **pending**.

## What your staff sees

When an appeal comes in, Banwatch posts it for your team with the user's message
and the two decision buttons. An appeal has one of three statuses:

| Status | Meaning |
| --- | --- |
| **Pending** | Submitted and waiting for your team to decide. |
| **Approved** | You chose to unban the user. |
| **Denied** | You chose to keep the ban in place. |

Once you decide, the user can't appeal that ban again unless they're re-banned
with `/reban` or you later accept the appeal.

## Handling abuse

If someone abuses the appeals system, open a ticket in the support server. Abuse
of this system can result in blacklisting from Banwatch.