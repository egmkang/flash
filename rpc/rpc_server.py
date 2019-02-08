from .rpc_codec import RpcRequest, RpcResponse, InitIDGenerator, RpcCodec
from .rpc_client import RpcClient
from .rpc_constant import *
from .rpc_future import GetFuture
from net.tcp_server import TcpServer
from net.tcp_connection import TcpConnection
from cluster.entity_position import *
from entity.player_manager import *
from utils.singleton import Singleton
from utils.log import *
from utils.local_ip import GetHostIp
from entity.entity import *
import logging
import logging.config
import uuid
import gevent


_global_method = dict()
_global_player_method = dict()
_player_manager = PlayerManager()
_position_manager = EntityPositionCache()


def rpc_method(fn):
    global _global_method
    name = fn.__name__
    _global_method[name] = fn
    return fn


def player_rpc_method(fn):
    global _global_player_method
    name = fn.__name__
    _global_player_method[name] = fn
    return fn


def _call_global_method(conn: TcpConnection, request: RpcRequest, response: RpcResponse):
    method = _global_method[request.method]
    try:
        result = method.__call__(*request.args, **request.kwargs)
        # TODO: 看看这边是不是需要支持future
        (response.error_code, response.response) = (ERROR_CODE_SUCCESS, result)
    except Exception as e:
        logger.error("handle_global_method, exception:%s" % e)
        (response.error_code, response.response) = (ERROR_CODE_INTERNAL, None)

    conn.send_message(response)


def _handle_global_method(request: RpcRequest, conn: TcpConnection):
    response = RpcResponse()
    response.request_id = request.request_id

    if request.method not in _global_method:
        response.error_code = ERROR_CODE_METHOD_NOT_FOUND
        response.response = None
        conn.send_message(response)
        return

    gevent.spawn(lambda: _call_global_method(conn, request, response))


#返回True表示中断
def _dispatch_entity_method_anyway(entity:Entity, conn: TcpConnection, request:RpcRequest, response:RpcResponse, method):
    try:
        entity.on_active()
    except Exception as e:
        logger.error("dispatch_entity_method, Entity:%s-%s, load fail, exception:%s" %
                     (request.entity_type, request.entity_id, e))
        (response.error_code, response.response) = (ERROR_CODE_PLAYER_LOAD, None)
        conn.send_message(response)
        return True

    try:
        result = method.__call__(entity, *request.args, **request.kwargs)
        # TODO: 看看这边是不是需要支持future
        (response.error_code, response.response) = (ERROR_CODE_SUCCESS, result)
        conn.send_message(response)
    except Exception as e:
        logger.error("dispatch_entity_method, Entity:%s-:%s method:%s, exception:%s" %
                     (request.entity_type, request.request_id, request.method, e))
    return False

def _dispatch_entity_method_loop(entity: Entity):
    context: RpcContext = entity.context()
    if context.running != False:
        return
    context.running = True

    try:
        while True:
            o = context.queue.get()
            if o is None:
                logger.info("entity:%s-%s exit", (entity.get_entity_type(), entity.get_uid()))
                break
            request: RpcRequest = o[1]

            context.host = request.host
            context.request_id = request.request_id

            need_break = _dispatch_entity_method_anyway(entity, *o)
            if need_break:
                break

            context.host = None
            context.request_id = None

    except Exception as e:
        logger.error("dispatch_entity_method_loop, entity:%s-%s, Exception:%s",
                     (entity.get_entity_type(), entity.get_uid(), e))
    entity.context().running = False
    pass


def _handle_player_method(request: RpcRequest, conn: TcpConnection):
    response = RpcResponse()
    response.request_id = request.request_id
    logger.info("handle player method, Player:%s, Method:%s" % (request.entity_id, request.method))
    if request.method not in _global_player_method:
        (response.error_code, response.response) = (ERROR_CODE_METHOD_NOT_FOUND, None)
        conn.send_message(response)
        return

    method = _global_player_method[request.method]
    player: Player = _player_manager.get_or_new_player(request.entity_id)
    if player is None:
        (response.error_code, response.response) = (ERROR_CODE_PLAYER_NOT_FOUND, None)
        conn.send_message(response)
        return

    if player.context().running is False:
        gevent.spawn(lambda: _dispatch_entity_method_loop(player))

    if player.context().host == request.host and player.context().request_id <= request.request_id:
        gevent.spawn(lambda: _dispatch_entity_method_anyway(player, conn, request, response, method))
        return
    player.context().SendMessage((conn, request, response, method))


def rpc_message_dispatcher(conn: TcpConnection, msg):
    if isinstance(msg, RpcRequest):
        _dispatch_request(conn, msg)
        pass
    else:
        # TODO: using gevent future
        future = GetFuture(msg.request_id)
        if future is None:
            logger.error("dispatch rpc response: %s, future not found" % (msg.request_id))
            return
        future.set_result(msg)
    pass


def _dispatch_request(conn: TcpConnection, request: RpcRequest):
    if request.entity_type == RPC_ENTITY_TYPE_GLOBAL:
        _handle_global_method(request, conn)
    if request.entity_type == RPC_ENTITY_TYPE_PLAYER:
        _handle_player_method(request, conn)


_server_unique_id = ""


def GetServerUniqueID():
    global _server_unique_id
    if len(_server_unique_id) <= 0:
        _server_unique_id = str(uuid.uuid4())
    return _server_unique_id


@Singleton
class RpcServer(TcpServer):
    def __init__(self, server_id):
        super().__init__()
        self.server_id = server_id
        self.client_pool = dict()
        InitIDGenerator(server_id)
        self._init_logger()
        self._init_machine_info()
        logger.info("ServerID:%d init" % server_id)
        logger.info("ServerUniqueID:%s init" % GetServerUniqueID())

    def _init_machine_info(self):
        self.machine_info = MachineInfo(self.server_id)
        self.machine_info.unique_id = GetServerUniqueID()
        self.etcd = EtcdHelper(host="119.27.187.221", port=2379)

    def _init_logger(self):
        logging.config.dictConfig(LOGGING_CONFIG_DEFAULTS)

    def listen_port(self, port):
        logger.info("listen port:%s" % port)
        self.listen(port, RpcCodec(), rpc_message_dispatcher)
        if self.machine_info.address is None:
            self.machine_info.address = (GetHostIp(), port)

    # TODO:
    # 需要有机制删除RpcConnection
    # 用Gevent重写
    def rpc_connect(self, host, port):
        key = (host, port)
        if key not in self.client_pool:
            client = RpcClient(host, port)
            self.client_pool[key] = client
            return client
        return self.client_pool[key]

    def run(self):
        _position_manager.set_etcd(self.etcd)
        gevent.spawn(lambda: UpdateMachineMemberInfo(self.machine_info, self.etcd))
        gevent.spawn(lambda: GetMembersInfo(self.etcd))

        while True:
            gevent.sleep(1.0)

