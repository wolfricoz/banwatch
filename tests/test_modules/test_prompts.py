import unittest
from unittest import mock

from classes import prompts


def fake_interaction(done=False) :
	interaction = mock.MagicMock()
	interaction.response.is_done.return_value = done
	interaction.response.defer = mock.AsyncMock()
	return interaction


class TestAskForMessage(unittest.IsolatedAsyncioTestCase) :
	"""ask_for_message() answers the interaction in time and turns a timeout into False (BANWATCH-GF)."""

	async def test_defers_and_returns_the_message(self) :
		interaction = fake_interaction()
		with mock.patch.object(prompts, "await_message", new=mock.AsyncMock(return_value="evidence")) :
			self.assertEqual(await prompts.ask_for_message(interaction, "prompt"), "evidence")
		interaction.response.defer.assert_awaited_once_with(ephemeral=True)

	async def test_does_not_defer_twice(self) :
		interaction = fake_interaction(done=True)
		with mock.patch.object(prompts, "await_message", new=mock.AsyncMock(return_value="evidence")) :
			await prompts.ask_for_message(interaction, "prompt")
		interaction.response.defer.assert_not_awaited()

	async def test_timeout_is_reported_and_returns_false(self) :
		interaction = fake_interaction()
		with mock.patch.object(prompts, "await_message", new=mock.AsyncMock(side_effect=TimeoutError)), \
				mock.patch.object(prompts, "send_response", new=mock.AsyncMock()) as send_response :
			self.assertIs(await prompts.ask_for_message(interaction, "prompt"), False)
		send_response.assert_awaited_once()

	async def test_cancel_is_passed_through(self) :
		interaction = fake_interaction()
		with mock.patch.object(prompts, "await_message", new=mock.AsyncMock(return_value=False)) :
			self.assertIs(await prompts.ask_for_message(interaction, "prompt"), False)


if __name__ == '__main__' :
	unittest.main()
