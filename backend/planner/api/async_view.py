"""DRF's request lifecycle with awaitable handlers and synchronous policy checks.

DRF APIView dispatch is synchronous. Keep its authentication, throttling and error
mapping while awaiting provider work directly on Django's ASGI event loop.
"""

from inspect import iscoroutinefunction
from typing import Any

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponseBase
from rest_framework.views import APIView


class AsyncAPIView(APIView):
    async def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.args, self.kwargs = args, kwargs
        wrapped = self.initialize_request(request, *args, **kwargs)
        self.request = wrapped
        self.headers = self.default_response_headers
        try:
            # DRF throttle/cache implementations can perform synchronous I/O.
            await sync_to_async(self.initial)(wrapped, *args, **kwargs)
            method = wrapped.method.lower()
            handler = (
                getattr(self, method, self.http_method_not_allowed)
                if method in self.http_method_names
                else self.http_method_not_allowed
            )
            if not callable(handler):
                handler = self.http_method_not_allowed
            response = (
                await handler(wrapped, *args, **kwargs)
                if iscoroutinefunction(handler)
                else await sync_to_async(handler)(wrapped, *args, **kwargs)
            )
        except Exception as exc:
            # Match DRF's dispatch boundary: map known errors and re-raise unknown ones.
            response = await sync_to_async(self.handle_exception)(exc)
        self.response = self.finalize_response(wrapped, response, *args, **kwargs)
        return self.response
