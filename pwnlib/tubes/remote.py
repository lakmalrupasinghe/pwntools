from .sock import sock
from ..timeout import Timeout
from ..log import getLogger
import socket
import ssl as _ssl

log = getLogger(__name__)

class remote(sock):
    r"""Creates a TCP or UDP-connection to a remote host. It supports
    both IPv4 and IPv6.

    The returned object supports all the methods from
    :class:`pwnlib.tubes.sock` and :class:`pwnlib.tubes.tube`.

    Arguments:
        host(str): The host to connect to.
        port(int): The port to connect to.
        fam: The string "any", "ipv4" or "ipv6" or an integer to pass to :func:`socket.getaddrinfo`.
        typ: The string "tcp" or "udp" or an integer to pass to :func:`socket.getaddrinfo`.
        timeout: A positive number, None or the string "default".
        ssl(bool): Wrap the socket with SSL
        sock(socket): Socket to inherit, rather than connecting

    Examples:

        >>> r = remote('google.com', 443, ssl=True)
        >>> r.send('GET /\r\n\r\n')
        >>> r.recvn(4)
        'HTTP'
        >>> r = remote('127.0.0.1', 1)
        Traceback (most recent call last):
        ...
        PwnlibException: Could not connect to 127.0.0.1 on port 1
        >>> import socket
        >>> s = socket.socket()
        >>> s.connect(('google.com', 80))
        >>> s.send('GET /' + '\r\n'*2)
        9
        >>> r = remote.fromsocket(s)
        >>> r.recvn(4)
        'HTTP'
    """

    def __init__(self, host, port,
                 fam = "any", typ = "tcp",
                 timeout = Timeout.default, ssl=False, sock=None):
        super(remote, self).__init__(timeout)

        self.rport  = int(port)
        self.rhost  = host

        if sock:
            self.family = sock.family
            self.type   = sock.type
            self.proto  = sock.proto
            self.sock   = sock

        else:
            typ = self._get_type(typ)
            fam = self._get_family(fam)
            self.sock   = self._connect(fam, typ)

        if self.sock:
            self.settimeout(self.timeout)
            self.lhost, self.lport = self.sock.getsockname()[:2]

            if ssl:
                self.sock = _ssl.wrap_socket(self.sock)


    @staticmethod
    def _get_family(fam):

        if isinstance(fam, (int, long)):
            pass
        elif fam == 'any':
            fam = socket.AF_UNSPEC
        elif fam.lower() in ['ipv4', 'ip4', 'v4', '4']:
            fam = socket.AF_INET
        elif fam.lower() in ['ipv6', 'ip6', 'v6', '6']:
            fam = socket.AF_INET6
        else:
            log.error("remote(): family %r is not supported" % fam)

        return fam

    @staticmethod
    def _get_type(typ):

        if isinstance(typ, (int, long)):
            pass
        elif typ == "tcp":
            typ = socket.SOCK_STREAM
        elif typ == "udp":
            typ = socket.SOCK_DGRAM
        else:
            log.error("remote(): type %r is not supported" % typ)

        return typ

    def _connect(self, fam, typ):
        sock    = None
        timeout = self.timeout

        h = log.waitfor('Opening connection to %s on port %d' % (self.rhost, self.rport))

        for res in socket.getaddrinfo(self.rhost, self.rport, fam, typ, 0, socket.AI_PASSIVE):
            self.family, self.type, self.proto, _canonname, sockaddr = res

            if self.type not in [socket.SOCK_STREAM, socket.SOCK_DGRAM]:
                continue

            h.status("Trying %s" % sockaddr[0])

            sock = socket.socket(self.family, self.type, self.proto)

            if timeout != None and timeout <= 0:
                sock.setblocking(0)
            else:
                sock.setblocking(1)
                sock.settimeout(timeout)

            try:
                sock.connect(sockaddr)
                break
            except socket.error:
                pass
        else:
            h.failure()
            log.error("Could not connect to %s on port %d" % (self.rhost, self.rport))

        h.success()
        return sock



    @classmethod
    def fromsocket(cls, socket):
        """
        Helper method to wrap a standard python socket.socket with the
        tube APIs.

        Arguments:
            socket: Instance of socket.socket

        Returns:
            Instance of pwnlib.tubes.remote.remote.
        """
        s = socket
        host, port = s.getpeername()
        return remote(host, port, fam=s.family, typ=s.type, sock=s)
