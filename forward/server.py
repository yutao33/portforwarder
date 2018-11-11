#!/usr/bin/env python3

import asyncio
import socket
import argparse

from forward.common import TCPServer,logger,Msg,readexactly,splice

class Server(TCPServer):
    def __init__(self, addr, port):
        super().__init__(addr,port)
        self.hosts = {}
        self.session_counter=0
        self.session_map = {} # sessionid -> (cr, cw) 

    async def handle_connect(self, sr, sw):
        addr = sw.get_extra_info('peername')
        logger.info("accept connect from %s" % str(addr))
        header=await readexactly(sr,Msg.HEADERLENGTH)
        bodylen = Msg.get_body_length(header)
        body = await readexactly(sr,bodylen)
        msgtype,datalen,info = Msg.info_unpack(header+body)
        if msgtype==Msg.CLIENTINSTRUCTION:
            hostname, addr, port = info
            logger.info("accept client %s %s:%d"%info)
            value=self.hosts.get(hostname)
            if value is None:
                sw.close()
                return
            _, tohostwriter = value
            if tohostwriter.transport.is_closing():
                logger.warn("to host writer is closing")
                sw.close()
                return
            self.session_counter+=1
            sessionid = self.session_counter
            tohostwriter.write(Msg.info_pack(Msg.SERVERINSTRUCTION, (addr, port, sessionid)))
            await tohostwriter.drain()
            self.session_map[sessionid]=(sr,sw)
            
        elif msgtype==Msg.SERVERINSTRUCTION:
            raise Error("error type")

        elif msgtype==Msg.HOSTINIT:
            hostname = info
            self.hosts[hostname]=(sr,sw)
            logger.info("accept host initial %s"%hostname)

        elif msgtype==Msg.HOSTSESSION:
            sessionid = info
            (cr,cw) = self.session_map[sessionid]
            await splice(cr,cw,sr,sw,self.loop)
            self.session_map.pop(sessionid)
        else:
            raise Error("unknown type")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--server",default="0.0.0.0",type=str,help="Server listen IP, default 0.0.0.0")
    parser.add_argument("-p","--port",default=9995,type=int,help="Server Port, default 9995s")
    args = parser.parse_args()
    Server(args.server, args.port).main_loop()


if __name__=="__main__":
    main()
