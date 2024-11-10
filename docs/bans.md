---
layout: default
title: Home
nav_order: 3
---

<h1 style="text-align: center;">Bans</h1>
<h6 style="text-align: center;">Learn how Banwatch handles bans, and about the suite of ban management commands.</h6>

## How are bans processed?
When you ban someone, Banwatch will automatically respond to this event and check if your server allows bans to be publicly shown, if the ban has  [hidden] tag or has no ban reason then these are logged as hidden bans by Banwatch. Hidden bans are never shown.

If you want the ban to be shown when someone uses the lookup command, but not be broadcasted you can add the [silent] tag to your ban message.

However now in version 3.0 when you do not add these, you will get an embed with the choices: 
* 'share': The ban will be broadcasted to all the servers where the user is present.
* 'share with proof': This will broadcast the ban after proof is supplied, proof helps other servers to make more informed choices. Evidence is also required for your ban to be verified by Banwatch staff.
* 'silent': This will not broadcast the ban, but the ban will not be hidden; meaning that when the user joins a server with Banwatch this ban will still be displayed to the staff of the server.
* 'hide': This completely hides the ban from all the servers, it will not be announced and only Banwatch staff can see it.

Once you've made your choice, Banwatch will fetch the ban and add it to the database with the staff member who added the ban; if the staff member is a bot it will default to the server owner. After this is done Banwatch will check for sensitive words (this list will not be public as we wish to avoid people from trying to bypass them). 

If a sensitive word is found then the ban must be approved by a Banwatch Staff member, this is to prevent harmful rumors to circulate without adequate proof. You may be requested to submit additional proof.

## Commands 

### `/ban user:(ping user or userid) ban_type:(optional), inform(optional, default: true), clean:(optional, default true)`
### `/mass-ban user_ids:(user id's divided by space) ban_type:(optional), inform(optional, default: true), clean:(optional, default true)`
These two commands are used to ban users. The ban_type option allows you to decide if its a silent or hidden ban, inform if the user will be dmed, and clean if you want the command to remove messages.

### `/unban user:(ping user or userid)`
### `/mass-unban user_ids:(user id's divided by space)`
These commands unban users, either a singular user or multiple users at a time.
### `/reban user:(ping user or userid) ban_type(optional) reason:(optional)`
This will unban the user and ban them again to update their ban reason, you will be prompted with a modal to fill in the ban reason. the reason option in the command is what will be shown when the ban is revoked.

### `/kick user:(ping user or userid)`
This command is used to kick users from your server.

### `/export_bans`
This will give you a text file with all the bans in your server, you can use this to quickly find bans.