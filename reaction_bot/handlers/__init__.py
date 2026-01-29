from .debug import router as debug_router
from .tasks import router as tasks_router
from .stats import router as stats_router
from .welcome import router as welcome_router

all_routers = [
    debug_router,
    welcome_router,
    tasks_router,
    stats_router,
]