#!/usr/bin/env python3

import asyncio
import socket
import argparse
import sys
import traceback

from forward.common import logger, Forwarder, splice, readexactly, Msg, parseIP



class Host:
    def __init__(self, server,port,hostname):
        self.server = server
        self.port = port
        self.hostname = hostname
        self.loop =  asyncio.new_event_loop()

    async def connect(self, addr, port, sessionid):
        try:
            hr, hw = await asyncio.open_connection(addr, port, loop=self.loop)
            sr, sw = await asyncio.open_connection(self.server, self.port, loop=self.loop)
            sw.write(Msg.info_pack(Msg.HOSTSESSION, sessionid))
            await splice(hr,hw,sr,sw,self.loop)
        except Exception:
            logger.warn("connect failed")

    async def controlLoop(self):
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.server, self.port, loop=self.loop)
                writer.write(Msg.info_pack(Msg.HOSTINIT, self.hostname))  # send hostname to server
                await writer.drain()
                while True:
                    header = await readexactly(reader, Msg.HEADERLENGTH)
                    bodylen = Msg.get_body_length(header)
                    body = await readexactly(reader,bodylen)
                    msgtype,datalen,info = Msg.info_unpack(header+body)
                    if msgtype==Msg.SERVERINSTRUCTION:
                        addr, port, sessionid = info
                        self.loop.create_task(self.connect(addr, port, sessionid))
                    else:
                        raise Error("unknown type")
            except Exception as e:
                logger.debug(str(e))
                logger.debug(traceback.print_exc())
                logger.error("control channel failed")
            asyncio.sleep(1)
            logger.info("reconnect to server")

    def _wakeup(self):
        self.loop.call_later(0.1, self._wakeup)

    def main_loop(self):
        loop = self.loop
        if sys.platform=="win32":
            loop.call_later(0.1,self._wakeup)
        loop.create_task(self.controlLoop())
        try:
            loop.run_forever()
        except KeyboardInterrupt as e:
            logger.error(str(e))
        except Exception as e:
            logger.error(str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--server",required=True,type=str,help="Remote server IP")
    parser.add_argument("-n","--hostname",required=True,type=str,help="Hostname")
    args = parser.parse_args()
    addr, port = parseIP(args.server)
    Host(addr, port, args.hostname).main_loop()


if __name__=="__main__":

    main()
