from classes.bans import Bans
from classes.cacher import LongTermCache
from classes.queue import queue
from classes.support.discord_tools import send_message, send_response


class EvidenceController():
    @staticmethod
    async def add_evidence(interaction, evidence, ban_id, channel, user):
        attachments = [await a.to_file() for a in evidence.attachments]
        if LongTermCache().get_ban(ban_id):
            queue().add(send_message(channel,
                                     f"Ban ID {ban_id} has been updated with new evidence:\n"
                                     f"{evidence.content}", files=attachments))
            queue().add(send_message(interaction.channel, f"Proof for {user.name}({user.id}) has been added to the evidence channel."))
            await evidence.delete()
            return
        # Could make this post the ban instead of ban_id not found, if the ban is approved.
        ban_entry, embed = await Bans().find_ban_record(interaction.client, ban_id)
        if ban_entry is None:
            queue().add(send_response(interaction, f"Ban ID {ban_id} not found."))
            return
        thread = await ban_entry.fetch_thread()
        if thread is None:
            thread = await ban_entry.create_thread(name=f"Evidence for {user.name}({user.id})")

        queue().add(thread.send(f"{evidence.content}", files=attachments))
        await evidence.delete()
