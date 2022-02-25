from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.options import parse_command_line
from kairon.shared.tornado.handlers.index import IndexHandler
from .handlers.action import ChatHandler, ReloadHandler
from .handlers.channels.slack import SlackHandler
from .handlers.channels.telegram import TelegramHandler
from .handlers.channels.hangouts import HangoutHandler
from ..shared.utils import Utility
from loguru import logger
from mongoengine import connect
Utility.load_environment()


def make_app():
    return Application([
        (r"/", IndexHandler),
        (r"/api/bot/([^/]+)/chat", ChatHandler),
        (r"/api/bot/slack/([^/]+)/([^/]+)", SlackHandler),
        (r"/api/bot/telegram/([^/]+)/([^/]+)", TelegramHandler),
        (r"/api/bot/hangout/([^/]+)/([^/]+)", HangoutHandler),
        (r"/api/bot/([^/]+)/reload", ReloadHandler),
    ], compress_response=True, debug=False)


if __name__ == "__main__":
    connect(**Utility.mongoengine_connection())
    app = make_app()
    Utility.initiate_tornado_apm_client(app)
    app.listen(5000)
    parse_command_line()
    logger.info("Server Started")
    IOLoop.current().start()