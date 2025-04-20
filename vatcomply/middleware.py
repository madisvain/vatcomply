import fcntl

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from django.conf import settings
from django.core.management import call_command


# ASGI middleware to run periodic tasks in the background
class BackgroundTasksMiddleware:
    def __init__(self, app):
        self.app = app
        self.scheduler = None
        self.lock_file = None

    async def __call__(self, scope, receive, send):
        if settings.BACKGROUND_SCHEDULER and scope["type"] == "lifespan":
            message = await receive()
            
            if message["type"] == "lifespan.startup":
                # Schedule rates updates and load initial data
                try:
                    # Lock file to prevent multiple instances of scheduler
                    self.lock_file = open("scheduler.lock", "w")
                    fcntl.lockf(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                    self.scheduler = AsyncIOScheduler()
                    self.scheduler.start()

                    # Fill up database with Countries
                    self.scheduler.add_job(lambda: call_command("load_countries"))

                    # Periodically updates lates 90 days Rates data
                    self.scheduler.add_job(
                        lambda: call_command("load_rates", last_90_days=True),
                        "interval",
                        hours=1,
                        minutes=10,
                    )

                    # Fill up database with Rates
                    self.scheduler.add_job(lambda: call_command("load_rates"))
                except BlockingIOError as e:
                    print(e)
                    
                # Send acknowledgement back
                await send({"type": "lifespan.startup.complete"})
                
            elif message["type"] == "lifespan.shutdown":
                # Clean up resources
                self._cleanup()
                
                # Send acknowledgement back
                await send({"type": "lifespan.shutdown.complete"})
                
                return

        return await self.app(scope, receive, send)
    
    def _cleanup(self):
        """Clean up resources to prevent memory leaks"""
        # Shutdown scheduler if it exists
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
            
        # Close file handle if it exists
        if self.lock_file:
            try:
                fcntl.lockf(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except (IOError, ValueError):
                pass
            self.lock_file = None
