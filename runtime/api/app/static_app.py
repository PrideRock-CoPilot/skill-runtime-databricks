from __future__ import annotations

from fastapi.staticfiles import StaticFiles


class SinglePageApp(StaticFiles):
    async def get_response(self, path: str, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        if response.status_code != 404:
            return response
        return await super().get_response("index.html", scope)