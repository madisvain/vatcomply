import fcntl

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from django.conf import settings
from django.core.management import call_command


# ASGI middleware to run periodic tasks in the background
class BackgroundTasksMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if settings.BACKGROUND_SCHEDULER and scope["type"] == "lifespan":
            message = await receive()
            if message["type"] == "lifespan.startup":
                # Schedule rates updates and load initial data
                try:
                    # Lock file to prevent multiple instances of scheduler
                    _ = open("scheduler.lock", "w")
                    fcntl.lockf(_.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                    scheduler = AsyncIOScheduler()
                    scheduler.start()

                    # Fill up database with Countries
                    scheduler.add_job(lambda: call_command("load_countries"))

                    # Periodically updates lates 90 days Rates data
                    scheduler.add_job(
                        lambda: call_command("load_rates", last_90_days=True),
                        "interval",
                        hours=1,
                        minutes=10,
                    )

                    # Fill up database with Rates
                    scheduler.add_job(lambda: call_command("load_rates"))
                except BlockingIOError as e:
                    print(e)

        return await self.app(scope, receive, send)
