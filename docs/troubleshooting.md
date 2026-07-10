---
layout: default
title: Troubleshooting
nav_order: 12
---

# Troubleshooting

Most Banwatch issues come down to permissions or the mod channel not being set.
Work through this page before contacting support — it fixes the large majority
of problems.

## Start here: the permission check

In your server, run:

```
/config permissioncheck
```

Banwatch replies with a ✅ / ❌ checklist. Any ❌ is very likely your problem.
To fix one:

1. Go to **Server Settings → Roles → Banwatch** and enable the missing
   permission, **and**
2. Check the mod channel itself — right-click it → **Edit Channel →
   Permissions**. A channel-level override can block Banwatch even when its role
   has the permission.

Then run the check again.

## Common problems

**Banwatch isn't posting anything.**
Usually the mod channel isn't set, or the bot can't talk in it. Run
`/config change` → *Mod Channel* to set it, then `/config permissioncheck` and
look at the "Can message in modchannel" line.

**It says it can't find or access my mod channel.**
The channel may have been deleted, or Banwatch lost access to it. Set it again
with `/config change`, choosing a channel Banwatch can clearly see and send
messages in.

**My existing bans didn't import.**
The import runs the first time you set the mod channel. If it didn't happen,
re-run `/config change` → *Mod Channel*. Expect a burst of messages while it
catches up.

**The bot can't ban, or lookups come back empty.**
Banwatch needs the **Ban Members** permission to read and apply bans. If it's
❌ in the permission check, that's the cause.

**A command says I don't have permission.**
Some commands require permissions on *you*, not the bot. For example `/config`
commands need **Manage Server**, and `/tools ban` needs **Ban Members**. Ask a
server admin to grant you the right role, or see [Permissions](permissions.md).

**Slash commands don't appear when I type `/`.**
Give Discord a minute after inviting the bot to register commands, then try
again. Fully closing and reopening Discord can help. Make sure the bot was
invited with the "commands" permission (use the invite link on the
[Getting Started](getting-started.md) page).

**A ban I hid still shows up in `/checkall`.**
The checkall list is cached and refreshes roughly every 10 minutes. Give it a
few minutes and it will drop off.

**A user is abusing appeals / spamming.**
Open a ticket in the support server. Abuse can lead to blacklisting from
Banwatch. See [Appeals](appeals.md).

## Still stuck?

- Run `/support` for a link to the support server — the best place to get help.
- Run `/config help` for in-app guidance.
- Have your `/config permissioncheck` result handy; it's the first thing support
  will ask about.
