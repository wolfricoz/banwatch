---
layout: default
title: Home
nav_order: 1
---

<h1 align="center">Banwatch</h1>
Build: 2.0<br>
Devs: ricostryker

Banwatch is a tool that allows you to monitor your server for bans in the roleplay community. It can be used to find
troublesome members and keep your server safe. By providing the ban reasons you gain more information about the ban and
can make a more informed decision about the user, whether to ban them or not. Banwatch also provides invites to the
server the user was banned from, so you can investigate further if needed.

banwatch manages more than 100 servers and has access to more than 6000 bans. It is a powerful tool that can help you
keep your server safe.

## Key Features

- Ban monitoring
- Being informed upon join about a ban
- Real time ban updates
- Invites to the server the user was banned from

## code of conduct

Banwatch has a code of conduct that all users must follow. The code of conduct is as follows:

- You must not use the bot to harass or bully other users by spreading false information.
- You must not use the bot to spam or flood the server.
- You must not use the bot to spread hate speech or any other form of discrimination.
- You must not use the bot to spread any form of illegal content.
- You must not use hate speech or any other form of discriminatory language in your ban reasons.
- We reserve the right to request proof of the ban reason if we suspect it is false or if the ban reason has a serious
  impact on the user's reputation.
- You must not pressure other users to ban an user if they do not want to. This includes threatening to ban them if they
  do not ban the user. __Banwatch is a tool to help you make informed decisions, not a tool to force others to ban
  users.__

## usage

To use banwatch, you need to invite the bot to your server. You can do this by
clicking [here](https://discord.com/oauth2/authorize?client_id=1047697525349564436). the bot requires the following
permissions:

- Manage server: This permission is required to set up the bot as well as access server invites and information.
- Ban members: This permission is required to check if a user has any bans, without the bot cant access bans.
- create instant invite: This allows the bot to create invites to the server the user was banned from.
- send messages: This permission is required to send messages to the channel you set up for the bot.
- use embedded activities: This permission is required to send embeds to the channel you set up for the bot.

After you have invited the bot to your server, you can set it up by using the `/config change option:Mod channel input:`
command. This command sets up the channel where the bot will post user-related information; once that is done, the bot
is ready to use and will work in the background to keep your server safe.

## Commands

Setting up the bot is straightforward and requires manage server permissions:

- `/config change option:Mod channel input:`: This command sets up the channel where the bot will post user-related
  information.

To monitor bans, you need ban member privileges:

- `/user lookup member:<user>`: Use this command to check if a specific user has any bans.

- `/user checkall`: This command checks all users in the server for any bans. The bot requires the ability to post
  files in the channel to use this command.
- `/support`: This command gives you a link to the documentation.

- `/appeal guild:<guildid>`: To appeal a ban, you can use this command. A modal will pop up where you can give your
  reason to be unbanned and the bot will send it to the server the user was banned from. You are only allowed to appeal
  once per server.

## Support

If you run into any issues or have any questions, you can join the support server by
clicking [here](https://discord.gg/sXqhbPxgGn). The support server is the best place to get help with the bot and to
report any issues you may encounter.

## Donations

This bot is free to use, but if you want to support the development of the bot, you can donate to the developer. This
will help keep the bot running and allow for more features to be added. You can donate by
clicking [here](https://donate.stripe.com/dR6eV63rQfr5g2kcMM).
