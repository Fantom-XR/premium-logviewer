__version__ = "1.1.1"

import base64
import os
from urllib.parse import urlencode, urlparse

import aiohttp
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from motor.motor_asyncio import AsyncIOMotorClient
from sanic import Sanic, response
from sanic.exceptions import NotFound, Unauthorized
from sanic_session import Session

from core.models import LogEntry
from core.utils import get_stack_variable, authrequired

load_dotenv()

OAUTH2_CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID")
OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET")
OAUTH2_REDIRECT_URI = os.getenv("OAUTH2_REDIRECT_URI")

API_BASE = "https://discordapp.com/api/"
AUTHORIZATION_BASE_URL = f"{API_BASE}/oauth2/authorize"
TOKEN_URL = f"{API_BASE}/oauth2/token"
ROLE_URL = f"{API_BASE}/guilds/{{guild_id}}/members/{{user_id}}"


if "URL_PREFIX" in os.environ:
    print("Using the legacy config var `URL_PREFIX`, rename it to `LOG_URL_PREFIX`")
    prefix = os.environ["URL_PREFIX"]
else:
    prefix = os.getenv("LOG_URL_PREFIX", "/logs")

if prefix == "NONE":
    prefix = ""

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("CONNECTION_URI")
if not MONGO_URI:
    print("No CONNECTION_URI config var found. "
          "Please enter your MongoDB connection URI in the configuration or .env file.")
    exit(1)

app = Sanic(__name__)
app.ctx.using_oauth = all((OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET, OAUTH2_REDIRECT_URI))
print("Using Oauth:", app.ctx.using_oauth)
if app.ctx.using_oauth:
    app.ctx.guild_id = os.environ["GUILD_ID"]
    app.ctx.bot_token = os.environ["TOKEN"]
    app.ctx.netloc = urlparse(OAUTH2_REDIRECT_URI).netloc
    app.ctx.bot_id = int(base64.b64decode(app.ctx.bot_token.split('.')[0] + '=='))

Session(app)
app.static("/static", "./static")

jinja_env = Environment(loader=FileSystemLoader("templates"))


def render_template(name, *args, **kwargs):
    template = jinja_env.get_template(name + ".html")
    request = get_stack_variable("request")
    if request:
        kwargs["session"] = request.ctx.session
        kwargs["user"] = request.ctx.session.get("user")
        kwargs['logged_in'] = kwargs["user"] is not None
    kwargs.update(globals())
    return response.html(template.render(*args, **kwargs))


app.ctx.render_template = render_template


@app.listener("before_server_start")
async def init(app, loop):
    app.ctx.db = AsyncIOMotorClient(MONGO_URI).modmail_bot
    app.ctx.client_session = aiohttp.ClientSession(loop=loop)


async def fetch_token(code):
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": OAUTH2_REDIRECT_URI,
        "client_id": OAUTH2_CLIENT_ID,
        "client_secret": OAUTH2_CLIENT_SECRET,
        "scope": "identify",
    }

    async with app.ctx.client_session.post(TOKEN_URL, data=data) as resp:
        json = await resp.json()
        return json


async def get_user_info(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with app.ctx.client_session.get(f"{API_BASE}/users/@me", headers=headers) as resp:
        return await resp.json()


async def get_user_roles(user_id):
    url = ROLE_URL.format(guild_id=app.ctx.guild_id, user_id=user_id)
    headers = {"Authorization": f"Bot {app.ctx.bot_token}"}
    async with app.ctx.client_session.get(url, headers=headers) as resp:
        user = await resp.json()
    return user.get("roles", [])


app.ctx.get_user_roles = get_user_roles


@app.exception(NotFound)
async def not_found(request, exc):
    return render_template("not_found")


@app.exception(Unauthorized)
async def not_authorized(request, exc):
    return render_template(
        "unauthorized", message="You do not have permission to view this page."
    )


@app.get("/")
async def index(request):
    request.ctx.session['last_visit'] = '/'
    return render_template("index")


@app.get("/login")
async def login(request):
    if "last_visit" not in request.ctx.session:
        request.ctx.session["last_visit"] = "/"

    data = {
        "scope": "identify",
        "client_id": OAUTH2_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": OAUTH2_REDIRECT_URI,
    }

    return response.redirect(f"{AUTHORIZATION_BASE_URL}?{urlencode(data)}")


@app.get("/callback")
async def oauth_callback(request):
    if request.args.get("error"):
        print("Failed to oauth")
        return response.redirect("/")

    code = request.args.get("code")
    token = await fetch_token(code)
    access_token = token.get("access_token")
    if access_token is not None:
        request.ctx.session["access_token"] = access_token
        request.ctx.session["user"] = await get_user_info(access_token)
        url = "/"
        if "last_visit" in request.ctx.session:
            url = request.ctx.session['last_visit']
        return response.redirect(url)
    return response.redirect("/login")


@app.get("/logout")
async def logout(request):
    request.ctx.session.clear()
    return response.redirect("/")


@app.get(prefix + "/raw/<key>")
@authrequired()
async def get_raw_logs_file(request, document):
    """Returns the plain text rendered log entry"""

    if document is None:
        raise NotFound

    log_entry = LogEntry(app, document)

    return log_entry.render_plain_text()


@app.get(prefix + "/<key>")
@authrequired()
async def get_logs_file(request, document):
    """Returns the html rendered log entry"""

    if document is None:
        raise NotFound

    log_entry = LogEntry(app, document)

    return log_entry.render_html()


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=os.getenv("PORT", 8000),
        debug=bool(os.getenv("DEBUG", False)),
    )
