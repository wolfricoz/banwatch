---
layout: default
title: FAQ
nav_order: 11
---

# Frequently asked questions

## Getting started

**What is Banwatch?**
Banwatch is a ban-management and early-warning tool for Discord communities. It
lets you look up a user's ban history across the network, warns you when a
flagged user joins your server, and notifies you when someone already in your
server is banned elsewhere. It currently tracks 45,000+ unique bans across 450+
contributing servers.

**Will Banwatch automatically ban my members?**
No. **Banwatch will never automatically ban users.** It informs you so you can
make your own decision. (The one exception is the opt-in premium *bot-trap*
feature, which you deliberately set up to ban anyone who clicks a trap button or
receives a trap role.)

**How do I add Banwatch to my server?**
Use the invite link:
<https://discord.com/oauth2/authorize?client_id=1047697525349564436>. Approve
the permissions, then run `/config change` to set your mod channel. See
[Permissions](permissions.md) for the full setup checklist.

**How do I set it up after inviting it?**
Run `/config change`, choose *Mod Channel*, and pick the channel where you want
Banwatch to post. On first setup Banwatch imports your existing bans, so expect
a burst of messages in that channel. After that it works in the background.

## Permissions & troubleshooting

**The bot isn't posting / doesn't seem to work. What do I check first?**
Run `/config permissioncheck`. It shows a ✅/❌ list of every permission Banwatch
needs and whether it can talk in your mod channel. Fix any ❌ (in role settings
**and** in channel overrides), then try again. Do this before contacting
support.

**Why does Banwatch need Ban Members permission?**
It's the core of the tool. Without it Banwatch cannot read your server's ban
list or apply bans you request, so it effectively can't function.

**Who in my server can configure the bot?**
Anyone with **Manage Server** can run the `/config` commands. Moderation
commands like `/tools ban` require the matching Discord permission (e.g. Ban
Members). See [Permissions](permissions.md).

## Bans, lookups & evidence

**How do I look up a user?**
Use `/lookup` with a user or a ban ID to see their ban history. `/checkall`
scans every current member of your server against the global ban database.

**Someone joined and Banwatch warned me — what does that mean?**
That user has a ban on record somewhere in the network. Banwatch shows you the
reason and any evidence so you can decide whether to act. It does not ban them
for you.

**What is evidence and how do I add it?**
Serious ban reasons can be backed by evidence (text or attachments). Add it with
`/evidence add`, view it with `/evidence get`, and manage it with
`/evidence manage`. Banwatch staff may request evidence for serious allegations
to keep the network accurate.

**What is a "verified" ban?**
A ban that Banwatch staff have reviewed and confirmed. Verification helps other
servers trust the accuracy of a ban record.

**Can I hide my server's bans from public lookups?**
Yes. Run `/config visibility` and set it to hidden. Note your bans may still
appear in the `checkall` cache for up to 10 minutes until it refreshes.

## Appeals

**Can banned users appeal?**
If you enable it. Run `/config appeals` to allow or disallow appeals for your
server. When enabled, users can submit an appeal that your staff can approve or
deny.

## Warnings

**Does Banwatch do warnings too?**
Yes. Use `/warnings warn` to warn a member, `/warnings manage` to review a
user's warnings, and `/warnings punishments` to set automatic actions (timeout,
kick, or ban) once a member reaches a warning threshold.

## Premium

**What do I get with premium?**
Premium adds features such as removing deleted accounts (`/premium
remove_deleted`), bot-trap buttons and roles, receiving all network bans,
cross-banning across servers you own, and preset ban reasons. See the
[Premium commands](commands/Premium.md).

## Privacy & data

**What data does Banwatch store?**
Ban records (user, reason, originating server), evidence you submit, and your
server's configuration. See the [Public privacy policy](publicprivacy.md) for
details.

**How do I contact support?**
Run `/support` for a link to the support server and documentation, or `/config
help` for in-app guidance.

**How can I support the project?**
Banwatch is free. If you'd like to help fund it, run `/donate` or use the
[donation link](https://buy.stripe.com/7sYbJ17fYeGY45bgygao803).
