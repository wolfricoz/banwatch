---
layout: default
title: Getting Started
nav_order: 2
---

# Getting started

Welcome to Banwatch! This page gets you up and running in about five minutes.
No technical knowledge needed — if you can invite a bot and pick a channel,
you're ready.

## What Banwatch does for you

Banwatch keeps your community safer by telling you about troublesome users
*before* they cause problems. It watches your bans, lets you look up a user's
history across the network, and warns you when someone with a history joins your
server. It never bans anyone for you — you always stay in control.

## Step 1 — Invite the bot

Click the invite link and choose your server:

<https://discord.com/oauth2/authorize?client_id=1047697525349564436>

Discord will show you a list of permissions. Leave them all checked — Banwatch
needs them to do its job. (Curious what each one is for? See
[Permissions](permissions.md).)


## Step 2 — Choose your mod channel

Tell Banwatch where to post by running:

```
/config change
```

Pick **Mod Channel** from the menu, then choose the channel you want (a private
staff channel works well). The first time you do this, Banwatch adds all of your
server's existing bans to its database, so don't be surprised by a burst of
messages — that's normal and only happens once.

That's it. Banwatch is now working in the background.

## Step 3 — Check the bot can work

In any channel, type:

```
/config permissioncheck
```

Banwatch replies with a tidy checklist. Every item should have a ✅. If you see
a ❌, head to **Server Settings → Roles → Banwatch** and turn that permission on,
then run the check again. This one command solves the majority of setup issues.



## Step 4 (optional) — Tune it to your liking

None of these are required, but they make Banwatch fit your server better:

- **Let users appeal bans** — `/config appeals`. See [Appeals](appeals.md).
- **Set an invite channel** so Banwatch can link back to a banned user's origin
  server — `/invite set_channel`.
- **Set up automatic warning punishments** — `/warnings punishments`. See
  [Warnings](warnings.md).
- **Hide your server's bans** from public lookups — `/config visibility`.

## What happens next?

- When someone with a ban on record joins your server, Banwatch quietly alerts
  your mod channel so your team can decide what to do.
- When you ban someone, Banwatch offers to share it with the network (with or
  without proof) so other communities can make informed decisions too. See
  [Bans](bans.md).

## Need a hand?

- Run `/config help` for in-app guidance.
- Run `/support` for a link to the support server.
- Browse the [FAQ](faq.md) or [Troubleshooting](troubleshooting.md).
