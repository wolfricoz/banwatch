---
layout: default
title: Home
nav_order: 3
---
<div style="text-align: center">
  <h1>Evidence</h1>
  <h6>This is how evidence works, and is used.</h6>
</div>

## What is evidence used for, and how is it stored?

When a user performs the command `/evidence add` or clicks the button `share with proof` when sharing their ban, the bot send a message in the channel informing the user that performed the command that their next message will be used as evidence.

Users can send text and files to be used as evidence, however **Currently you can not use discord's forward function**. When these are sent they are added in to the database and matched to the ban; if the ban is being reviewed the staff will immediately be shown this evidence so that we can base our judgements upon them.

Evidence can be viewed by other servers and it's  great way to inform other servers if you make a ban; you can store as much proof as you'd like - see it as a way to keep all your logging in one place!

Do's:
* Provide evidence with enough context.
* Blur out unrelated names, we don't want to create targets for harassment.
* Provide both text describing what happened, and pictures or videos to back up those claims.

Dont's:
* Don't insult the user in your evidence.
* Include unrelated information (i.e the user has a cat).
* Search the support server for evidence to use; if you are banning based upon another ban please put 'cross-ban' infront of your ban.



## Commands
### `/evidence add user:(user or uid)`
NOTE: You should do this in the server you banned them in.
When you run this command it ask you to provide evidence in the form of a discord message, this means you can include text AND attachments such as text files, images, and videos. These will then be linked to the user's ban or throw an exception if there is no ban found

By using this command you consent to the content of the message being saved.

### `/evidence get user:(user or uid) ban_id:(ban_id)`
You have to fill in either user or ban_id, do not fill in both.
If you fill in user you get all the evidence there is, from all the bans
if you use ban_id, you get only evidence from one specific ban.

### `/evidence manage user:(user or uid) ban_id:(ban_id)`
You have to fill in either user or ban_id, do not fill in both.
This command allows you to view all the evidence of a specific ban or user and manage them; this includes removing them if you're the original server who made the evidence. 