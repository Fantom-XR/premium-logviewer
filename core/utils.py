from functools import wraps

import sanic.exceptions
from sanic import response
import inspect
import asyncio


def get_stack_variable(name):
    stack = inspect.stack()
    try:
        for frames in stack:
            try:
                frame = frames[0]
                current_locals = frame.f_locals
                if name in current_locals:
                    return current_locals[name]
            finally:
                del frame
    finally:
        del stack


def authrequired():
    def decorator(func):
        @wraps(func)
        async def wrapper(request, key):
            app = request.app

            if not app.ctx.using_oauth:
                return await func(request, await app.ctx.db.logs.find_one({"key": key}))

            if request.ctx.session.get('user') is None:
                request.ctx.session["last_visit"] = request.url
                return response.redirect("/login")

            user = request.ctx.session["user"]

            config, document = await asyncio.gather(
                app.ctx.db.config.find_one({"bot_id": int(app.ctx.bot_id)}),
                app.ctx.db.logs.find_one({"key": key}),
            )

            if not config:
                raise sanic.exceptions.ServiceUnavailable("Please setup your bot before viewing logs.")

            whitelist = config.get("oauth_whitelist", [])
            if document:
                whitelist.extend(document.get("oauth_whitelist", []))

            if int(user["id"]) in whitelist or "everyone" in whitelist:
                return await func(request, document)

            roles = await app.ctx.get_user_roles(user["id"])

            if any(int(r) in whitelist for r in roles):
                return await func(request, document)

            raise sanic.exceptions.Unauthorized("Your account does not have permission to view this page.")

        return wrapper

    return decorator
