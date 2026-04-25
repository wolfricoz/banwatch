import ipaddress
import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request, status

from project.whitelist import API_IP_WHITELIST

load_dotenv('main.env')

class Auth():
	"""
	"""
	_TOKEN = os.getenv("RPSECSECRET")

	_request: Request = None
	_user_token: str | None = None


	def __init__(self, request: Request):
		self._request = request

	async def verify(self) :
		"""
		This is the main authentication method, it will call all other methods and verify the user's login.
		"""
		# Get auth token from headers
		await self.get_auth_token()

		# Check auth token with .env
		await self.validate_auth_token()

		# Check IP whitelist (if set.)
		await self.check_ip_whitelist()

		# To ensure that no data is kept in the class, we clear it.
		await self.clear_data()

		# If everything matches, return true.
		return True


	# Support functions

	async def get_auth_token(self) -> None:
		"""
		Gets the auth token from the header
		"""
		self._user_token = self._request.headers.get("X-Auth-Token")

	async def validate_auth_token(self) -> bool:
		"""
		We check if the user's token matches the application's token.
		"""
		if not self._user_token:
			raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
		if not self._TOKEN:
			raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED)

		if self._user_token == self._TOKEN:
			return True
		raise HTTPException(status_code=403)


	async def check_ip_whitelist(self) -> bool:
		"""
		We check if the user's IP address matches the application's IP whitelist.
		"""
		if not API_IP_WHITELIST:
			# If no whitelist is set, we just set it to true.
			return True
		client_ip = self._request.client.host


		try :
			# Check openVPN ranges
			vpn_subnet = ipaddress.ip_network('10.8.0.0/24')

			if ipaddress.ip_address(client_ip) in vpn_subnet :
				return True

			if client_ip in API_IP_WHITELIST :
				return True

		except ValueError :
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed IP")
		raise HTTPException(status_code=403)




	async def clear_data(self):
		"""
		Clears the data from the class to prevent it being used in other instances.
		"""
		self._request = None
		self._user_token = None



