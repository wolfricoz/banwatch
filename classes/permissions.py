import discord
from discord_py_utilities.messages import send_response, send_message
from discord_py_utilities.permissions import check_missing_channel_permissions


class PermissionsCheck():

    async def permission_check(self, interaction: discord.Interaction, channel = None):
        await send_response(interaction, "⌛ Checking permissions...", ephemeral=True)
        permissions = {
            "Ban Members": interaction.guild.me.guild_permissions.ban_members,
            "Kick Members": interaction.guild.me.guild_permissions.kick_members,
            "Manage Guild": interaction.guild.me.guild_permissions.manage_guild,
            "Create Invite": interaction.guild.me.guild_permissions.create_instant_invite,
            "Embedded Activities": interaction.guild.me.guild_permissions.use_embedded_activities,
            "View Audit Log": interaction.guild.me.guild_permissions.view_audit_log,
            "Manage Messages": interaction.guild.me.guild_permissions.manage_messages,
            "Send Messages": interaction.guild.me.guild_permissions.send_messages,
            "Attach Files": interaction.guild.me.guild_permissions.attach_files,
        }
        if channel is None:
            channel = interaction.channel

        missing = check_missing_channel_permissions(channel,
                                                    ['view_channel', 'send_messages', 'embed_links', 'attach_files'])
        permission_status = {
            "Ban_members": "✅" if "ban_members" in permissions else "❌",
            "Kick_members": "✅" if "kick_members" in permissions else "❌",
            "Manage_guild": "✅" if "manage_guild" in permissions else "❌",
            "Create_instant_invite": "✅" if "create_instant_invite" in permissions else "❌",
            "Use_embedded_activities": "✅" if "use_embedded_activities" in permissions else "❌",
            "View_audit_log": "✅" if "view_audit_log" in permissions else "❌",
            "Manage_messages": "✅" if "manage_messages" in permissions else "❌",
            "Send_messages": "✅" if "send_messages" in permissions else "❌",
            "Attach_files": "✅" if "attach_files" in permissions else "❌",
            "Can message in modchannel": "✅" if len(missing) <= 1 else "❌",
        }
        embed = discord.Embed(title="Permissions Check", color=0x00ff00)
        embed.description = f"I have the following permissions in {interaction.guild.name}::"
        for key, value in permission_status.items():
            embed.add_field(name=key, value=value, inline=False)
        try:
            await send_message(channel, embed=embed)
        except:
            await send_message(interaction.user, embed=embed, error_mode='ignore')
