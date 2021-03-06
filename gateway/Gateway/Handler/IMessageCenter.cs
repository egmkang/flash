﻿using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Gateway.Message;
using Gateway.Network;

namespace Gateway.Handler
{
    public delegate Task MessageCallback(ISession session, RpcMeta meta, byte[] body);
    public delegate Task WebSocketMessage(ISession session, Memory<byte> memory, int size);
    public delegate Task WebSocketClose(ISession session);

    public interface IMessageCenter
    {
        /// <summary>
        /// 注册消息的回调
        /// </summary>
        /// <param name="type">类型, NULL的时候, 就是默认的处理函数</param>
        /// <param name="handler">回调函数</param>
        void RegisterMessageCallback(Type type, MessageCallback handler);

        void RegisterWebSocketCallback(WebSocketMessage messageCallback, WebSocketClose closeCallback);

        Task OnWebSocketClose(ISession session);
        Task OnWebSocketMessage(ISession session, Memory<byte> memory, int size);

        Task OnSocketClose(ISession session);
        Task OnSocketMessage(ISession session, RpcMeta rpcMeta, byte[] body);

        Task SendMessageToSession(long sessionID, object msg);
        Task SendMessageToServer(long serverID, object msg);
    }
}
