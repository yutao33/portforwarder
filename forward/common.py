import asyncio
import socket
import logging
import sys
import struct

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def parseIP(s):
    addr, port = s.split(":")
    port=int(port)
    return addr, port


class Forwarder:
    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer

    async def loop(self):
        logger.info("start forward loop")
        try:
            while True:
                data = await self._reader.read(1024)
                if len(data)==0:
                    break
                logger.debug("received %s"%str(data))
                await self._writer.drain()
                self._writer.write(data)
        except Exception:
            pass
        logger.info('end forward loop')
        self._writer.close()


async def splice(r1,w1,r2,w2,loop):
    loop.create_task(Forwarder(r1,w2).loop())
    await Forwarder(r2,w1).loop()


async def readexactly(reader, length):
    data = b''
    while length>0:
        r = await reader.read(length)
        if len(r)==0:
            raise Exception('read length == 0')
        data+=r
        length-=len(r)
    return data


class Msg:
    CLIENTINSTRUCTION=1 # client to server instruction
    SERVERINSTRUCTION=2 # server to host instruction
    HOSTINIT=3          # client to server initial hostname
    HOSTSESSION=4       # client to server host session

    HEADERLENGTH=8

    @staticmethod
    def info_pack(msgtype, info):
        if msgtype==Msg.CLIENTINSTRUCTION:
            hostname, addr, port = info
            s="%s %s %d"%(hostname,addr,port)
            body = s.encode()
        elif msgtype==Msg.SERVERINSTRUCTION:
            addr, port, sessionid = info
            s="%s %d %d"%(addr, port, sessionid)
            body = s.encode()
        elif msgtype==Msg.HOSTINIT:
            hostname = info
            body = hostname.encode()
        elif msgtype==Msg.HOSTSESSION:
            sessionid = str(info)
            body = sessionid.encode()
        return struct.pack("!II",msgtype,len(body))+body
    
    @staticmethod
    def get_body_length(headerbytes):
        assert len(headerbytes)==Msg.HEADERLENGTH
        msgtype,datalen = struct.unpack("!II",headerbytes)
        return datalen

    @staticmethod
    def info_unpack(data):
        msgtype,datalen = struct.unpack("!II",data[0:8])
        body = data[8:8+datalen]
        if msgtype==Msg.CLIENTINSTRUCTION:
            s = body.decode()
            hostname, addr, port = s.split(" ")
            port = int(port)
            info = (hostname, addr, port)
        elif msgtype==Msg.SERVERINSTRUCTION:
            s = body.decode()
            addr, port, sessionid = s.split(" ")
            port = int(port)
            sessionid = int(sessionid)
            info = (addr, port, sessionid)            
        elif msgtype==Msg.HOSTINIT:
            s = body.decode()
            hostname = s
            info = hostname
        elif msgtype==Msg.HOSTSESSION:
            s = body.decode()
            sessionid = int(s)
            info = sessionid
        return msgtype,datalen,info


class TCPServer:
    def __init__(self, addr, port):
        self._addr = addr
        self._port = port
        self.loop = asyncio.new_event_loop()
        self._server = None

    def _wakeup(self):
        self.loop.call_later(0.1, self._wakeup)
    
    def main_loop(self):
        logger.info("main_loop")
        loop = self.loop
        # tmp workaround
        if sys.platform=="win32":
            loop.call_later(0.1,self._wakeup)
        self.start_server()
        try:
            loop.run_forever()
        except KeyboardInterrupt as e:
            logger.error("KeyboardInterrupt")
        except Exception as e:
            logger.error(str(e))
        logger.warn("run_forever exited")
        self._server.close()
        logger.warn("self._server.close")
        loop.run_until_complete(self._server.wait_closed())
        logger.warn("self._server.wait_closed()")
        loop.close()

    def start_server(self):
        coro = asyncio.start_server(self.handle_connect,
                                    self._addr,
                                    self._port,
                                    family = socket.AF_INET,
                                    loop=self.loop)
        self._server = self.loop.run_until_complete(coro)
        logger.info('Serving on {}'.format(self._server.sockets[0].getsockname()))

    def stop(self):
        def _stop():
            self.loop.stop()
        self.loop.call_soon_threadsafe(_stop)

    async def handle_connect(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info("accept connect from %s" % str(addr))
        writer.write(b"test")
        await writer.drain()
        writer.close()


if __name__=="__main__":
    TCPServer("0.0.0.0",9995).main_loop()
