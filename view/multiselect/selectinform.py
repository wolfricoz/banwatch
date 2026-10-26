import discord.ui

from view.base.secureview import SecureView

# Every preset tells the server the same thing: the ban is hidden until evidence arrives. Submitting
# evidence through the request (or /evidence add) puts the ban back in the review queue; a re-ban does
# not, because the hidden flag survives a re-add.
EVIDENCE_FOOTER = (" This ban will be hidden for the time being. Please submit evidence using the button below "
                   "or `/evidence add`, and the ban will be reviewed again.")

INFORM_PRESETS = [
	{
		"label"       : "Custom",
		"description" : "Select this to write your own message",
		"message"     : "custom",
		"emote"       : "📝"
	},
	{
		"label"       : "Proof required (generic)",
		"description" : "Some, if not all, of the claims require proof to be broadcast",
		"message"     : "Some, if not all, of your claims require proof to be broadcast." + EVIDENCE_FOOTER,
		"emote"       : "📎"
	},
	{
		"label"       : "Serious allegation",
		"description" : "Harassment, threats, doxxing, hate speech or similar claims",
		"message"     : "This ban contains serious allegations (such as harassment, threats, doxxing or hate speech) "
		                "which we can only broadcast with proof." + EVIDENCE_FOOTER,
		"emote"       : "⚠️"
	},
	{
		"label"       : "Underage / age claims",
		"description" : "Claims about the user's age need proof",
		"message"     : "Claims about a user's age can only be broadcast with proof, such as the user stating their "
		                "age. Please blur out any personal information." + EVIDENCE_FOOTER,
		"emote"       : "🎂"
	},
	{
		"label"       : "Evidence unclear",
		"description" : "The current evidence does not clearly show the claims",
		"message"     : "The evidence currently on this ban does not clearly show the claims in the ban reason. "
		                "Please provide evidence that does, with context where needed." + EVIDENCE_FOOTER,
		"emote"       : "🔍"
	},
	{
		"label"       : "Personal information in evidence",
		"description" : "The evidence contains PII that must be removed",
		"message"     : "The evidence on this ban contains personal information (such as real names, addresses, "
		                "phone numbers, dates of birth or government documents). We cannot broadcast this. Please "
		                "resubmit the evidence with all personal information removed or blurred out." + EVIDENCE_FOOTER,
		"emote"       : "🔒"
	},
	{
		"label"       : "Off-server behavior",
		"description" : "Claims about behavior in DMs or other servers",
		"message"     : "This ban refers to behavior outside of your server (DMs or other communities). We need proof "
		                "of this behavior before it can be broadcast." + EVIDENCE_FOOTER,
		"emote"       : "🌐"
	},
]


class InformSelect(discord.ui.Select) :
	def __init__(self) :
		options = [
			discord.SelectOption(
				label=preset['label'][:99],
				value=preset['label'][:99],
				description=preset['description'][:99],
				emoji=preset['emote']
			)
			for preset in INFORM_PRESETS
		]

		super().__init__(
			placeholder="Select the message to send the server",
			options=options,
			min_values=1,
			max_values=1
		)

	# ============================================================
	async def callback(self, interaction: discord.Interaction) :
		self.view.selected = self.values[0]
		self.view.interaction = interaction
		self.view.stop()


class SelectInform(SecureView) :
	def __init__(self) :
		super().__init__(timeout=600)
		self.selected = None
		self.interaction = None
		self.add_item(InformSelect())

	# ============================================================
	def get_message(self) :
		"""The preset message for the selected option, "custom" for a custom message, or None if nothing was picked."""
		if not self.selected :
			return None
		for preset in INFORM_PRESETS :
			if preset['label'][:99] == self.selected :
				return preset['message']
		return None
