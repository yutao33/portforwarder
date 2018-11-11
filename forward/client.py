#!/usr/bin/env python3

import asyncio
import socket
import argparse

from forward.common import TCPServer,logger,parseIP,splice,Msg

class Server(TCPServer):
    def __init__(self, local_addr, local_port, server_addr, server_port, hostname, remote_addr, remote_port):
        super().__init__(local_addr,local_port)
        self.server_addr = server_addr
        self.server_port = server_port
        self.hostname = hostname
        self.remote_addr = remote_addr
        self.remote_port = remote_port

    async def handle_connect(self, cr, cw):
        addr = cw.get_extra_info('peername')
        logger.info("accept connect from %s" % str(addr))
        sr, sw = await asyncio.open_connection(self.server_addr, self.server_port, loop=self.loop)
        sw.write(Msg.info_pack(Msg.CLIENTINSTRUCTION,(self.hostname,self.remote_addr,self.remote_port)))
        await splice(sr,sw,cr,cw,self.loop)


# python client.py -l 127.0.0.1:10009 -s 127.0.0.1:9995 -n 1 -r 127.0.0.1:8080
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l","--local",default="127.0.0.1:10009",type=str,help="Local listen IP, default 127.0.0.1:9995")
    parser.add_argument("-s","--server",required=True,type=str,help="Remote server IP")
    parser.add_argument("-n","--hostname",required=True,type=str,help="Remote host name")
    parser.add_argument("-r","--remote",default="127.0.0.1:8080",type=str,help="Mapped remote address")
    args = parser.parse_args()
    local_addr, local_port = parseIP(args.local)
    server_addr, server_port = parseIP(args.server)
    hostname = args.hostname
    remote_addr, remote_port = parseIP(args.remote)
    Server(local_addr, local_port, server_addr, server_port, hostname, remote_addr, remote_port).main_loop()


if __name__=="__main__":
    main()
