import enum

evidence_message_template = (
  "Please send a message with the evidence you would like to add to {user}'s record, this will be added to the ban ID {ban_id} in our support server and broadcasted to relevant servers."
  "\n Type `cancel` to cancel."
  "\nPlease avoid uploading:"
  "\n* Personal information (irl information such as a persons name, date of birth, where they live, government documentation, etc)"
  "\n* We recommend you blur out any usernames or profile pictures of other users in the evidence for user safety."
  "\n* Please do not upload any illegal content such as CP. If you have evidence of this please contact the authorities and Discord Trust & Safety immediately."
  "\n* Please sufficiently black out any NSFW content in the evidence; we prefer to not broadcast NSFW content"
  "\n\n**Forwarded Messages are now officially supported.**")


evidence_warning_message_template = (
  "Please send a message with the evidence you would like to add to {user}'s record, this will be added to the warning ID {warning_id} locally (Only your server can see it!)."
  "\n Type `cancel` to cancel."
  "\nPlease avoid uploading:"
  "\n* Illegal content such as CP. If you have evidence of this please contact the authorities and Discord Trust & Safety immediately."
  "\n\n**Forwarded Messages are now officially supported.**")

class BotMessages(enum.Enum):
	BLACKISTED = "🚫 You are blacklisted from using this bot."

	def __str__(self):
		return self.value