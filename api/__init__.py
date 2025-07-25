from .bans import router as bans_router
from .config import router as config_router
from .status import router as status_router
from .sentry import router as sentry_router
__all__ = ["bans_router", "config_router", "status_router", "sentry_router"]