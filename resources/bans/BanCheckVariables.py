# Every entry here is compared against a NORMALISED reason (see BanChecker.normalise_reason): lower
# case, leading [silent]/[hidden] tags removed and surrounding punctuation stripped. Keep entries
# lower case and unpadded, or they will never match.
IGNORED_REASONS = (
	"",
	"none",
	"account has no avatar",
	"no reason",
	"no reason given",
	"no reason provided",
	"breaking server rules",
	"n/a",
	"test"
)

BAN_STARTS_WITH = (
	"[hidden]",
	"no pfp",
	"account has no avatar"
)

# Tags that moderators (or /ban, /reban) put in front of a reason. They say how the ban should be
# shared, not why the user was banned, so the rules look past them.
REASON_TAGS = (
	"silent",
	"hidden",
)
