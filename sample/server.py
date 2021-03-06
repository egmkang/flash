from koala.conf.loader import load_config
from koala.placement.placement import *
from koala.pd.placement import *
from koala.server import server_base
import sample.interfaces
import sample.player
from sample.account import *
import os


_config = Config()


def init_server():
    _pd_impl = PDPlacementImpl(_config.pd_address)
    set_placement_impl(_pd_impl)

    server_base.init_server()
    server_base.register_user_handler(
        RequestAccountLogin, process_gateway_account_login)


def run_server():
    server_base.listen_rpc(_config.port)
    server_base.run_server()


load_config(f"{os.getcwd()}/sample/app.yaml")
init_server()
run_server()
