import asyncio
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

from django.test import SimpleTestCase, override_settings

from vatcomply.middleware import BackgroundTasksMiddleware


class TestBackgroundTasksMiddleware(SimpleTestCase):
    # Helper method to run async tests
    def async_test(self, coro):
        return asyncio.run(coro)
    @override_settings(BACKGROUND_SCHEDULER=True)
    @patch('fcntl.lockf')
    @patch('builtins.open', new_callable=mock_open)
    @patch('vatcomply.middleware.AsyncIOScheduler')
    def test_startup_initializes_resources(self, mock_scheduler_class, mock_file, mock_lockf):
        async def _test():
            # Setup
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            
            # Create middleware
            app = AsyncMock()
            middleware = BackgroundTasksMiddleware(app)
            
            # Mock lifespan scope and messages
            scope = {"type": "lifespan"}
            send = AsyncMock()
            
            # Create a receive function that returns a startup message
            async def receive():
                return {"type": "lifespan.startup"}
            
            # Call middleware
            await middleware(scope, receive, send)
            
            # Assert resources were initialized
            self.assertIsNotNone(middleware.lock_file)
            self.assertIsNotNone(middleware.scheduler)
            
            # Assert lock file was opened
            mock_file.assert_called_once_with("scheduler.lock", "w")
            
            # Assert scheduler was started
            mock_scheduler.start.assert_called_once()
            
            # Assert jobs were added
            self.assertEqual(mock_scheduler.add_job.call_count, 3)
            
            # Assert startup complete message was sent
            send.assert_called_once_with({"type": "lifespan.startup.complete"})
            
        # Run the async test
        self.async_test(_test())
    
    @override_settings(BACKGROUND_SCHEDULER=True)
    @patch('fcntl.lockf')
    @patch('builtins.open', new_callable=mock_open)
    @patch('vatcomply.middleware.AsyncIOScheduler')
    def test_shutdown_cleans_up_resources(self, mock_scheduler_class, mock_file, mock_lockf):
        async def _test():
            # Setup
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            mock_file_handle = mock_file()
            
            # Create middleware
            app = AsyncMock()
            middleware = BackgroundTasksMiddleware(app)
            
            # Mock lifespan scope
            scope = {"type": "lifespan"}
            send = AsyncMock()
            
            # First send startup message to initialize resources
            async def receive_startup():
                return {"type": "lifespan.startup"}
            
            await middleware(scope, receive_startup, send)
            
            # Reset mocks for testing shutdown
            send.reset_mock()
            
            # Now send shutdown message
            async def receive_shutdown():
                return {"type": "lifespan.shutdown"}
            
            await middleware(scope, receive_shutdown, send)
            
            # Assert cleanup was performed
            mock_scheduler.shutdown.assert_called_once()
            self.assertIsNone(middleware.scheduler)
            
            # Assert file was closed
            mock_file_handle.close.assert_called_once()
            self.assertIsNone(middleware.lock_file)
            
            # Assert shutdown complete message was sent
            send.assert_called_once_with({"type": "lifespan.shutdown.complete"})
            
        # Run the async test
        self.async_test(_test())
    
    @override_settings(BACKGROUND_SCHEDULER=True)
    @patch('fcntl.lockf', side_effect=BlockingIOError("Resource temporarily unavailable"))
    @patch('builtins.open', new_callable=mock_open)
    @patch('vatcomply.middleware.AsyncIOScheduler')
    def test_handles_blocking_error(self, mock_scheduler_class, mock_file, mock_lockf):
        async def _test():
            # Create middleware
            app = AsyncMock()
            middleware = BackgroundTasksMiddleware(app)
            
            # Mock lifespan scope
            scope = {"type": "lifespan"}
            send = AsyncMock()
            
            # Create a receive function that returns a startup message
            async def receive():
                return {"type": "lifespan.startup"}
            
            # Call middleware - this should handle the BlockingIOError
            with patch('builtins.print') as mock_print:
                await middleware(scope, receive, send)
            
            # Assert BlockingIOError was caught and printed
            mock_print.assert_called_once()
            
            # Assert scheduler was not initialized due to the exception
            self.assertIsNone(middleware.scheduler)
            
            # Assert startup complete message was still sent
            send.assert_called_once_with({"type": "lifespan.startup.complete"})
        
        # Run the async test
        self.async_test(_test())
    
    @override_settings(BACKGROUND_SCHEDULER=False)
    def test_skips_scheduling_when_disabled(self):
        async def _test():
            # Create middleware
            app = AsyncMock()
            middleware = BackgroundTasksMiddleware(app)
            
            # Mock lifespan scope
            scope = {"type": "lifespan"}
            send = AsyncMock()
            
            # Create a receive function that returns a startup message
            async def receive():
                return {"type": "lifespan.startup"}
            
            # Call middleware
            with patch('vatcomply.middleware.AsyncIOScheduler') as mock_scheduler_class:
                await middleware(scope, receive, send)
            
            # Assert scheduler was not created
            mock_scheduler_class.assert_not_called()
            
            # Assert app was called
            app.assert_called_once_with(scope, receive, send)
        
        # Run the async test
        self.async_test(_test())
        
    def test_passes_non_lifespan_requests(self):
        async def _test():
            # Create middleware
            app = AsyncMock()
            app.return_value = "response"
            middleware = BackgroundTasksMiddleware(app)
            
            # Mock non-lifespan scope
            scope = {"type": "http"}
            receive = AsyncMock()
            send = AsyncMock()
            
            # Call middleware
            result = await middleware(scope, receive, send)
            
            # Assert app was called with original parameters
            app.assert_called_once_with(scope, receive, send)
            
            # Assert result is what the app returned
            self.assertEqual(result, "response")
        
        # Run the async test
        self.async_test(_test())