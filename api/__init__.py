from .bans import router as bans_router
from .config import router as config_router
from .status import router as status_router
__all__ = ["bans_router", "config_router", "status_router"]