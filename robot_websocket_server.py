
import json
from _thread import allocate_lock
import robot
from MicroWebSrv2 import *


def websocket_on_accept(microWebSrv2, webSocket):
    print('Example WebSocket accepted:')
    print('   - User   : %s:%s' % webSocket.Request.UserAddress)
    print('   - Path   : %s' % webSocket.Request.Path)
    print('   - Origin : %s' % webSocket.Request.Origin)
    if webSocket.Request.Path.lower() == '/controller_ws':
        controller_websocket_join(webSocket)
    elif webSocket.Request.Path.lower() == '/motors_ws':
        motors_websocket_join(webSocket)
    else:
        print('Uknown ws path: "%s"' % webSocket.Request.Path.lower())
        webSocket.OnTextMessage = websocket_on_recv_text
        webSocket.OnBinaryMessage = websocket_on_recv_binary
        webSocket.OnClosed = websocket_on_close
        webSocket.Close()

# ============================================================================
# ============================================================================
# ============================================================================


global controller_ws
controller_ws = None
global motors_ws
motors_ws = None

global _wsLock
_wsLock = allocate_lock()


def websocket_on_recv_text(webSocket, msg):
    pass

# ------------------------------------------------------------------------


def websocket_on_recv_binary(webSocket, msg):
    pass

# ------------------------------------------------------------------------


def websocket_on_close(webSocket):
    global controller_ws, motors_ws
    print('WebSocket %s:%s closed' % webSocket.Request.UserAddress)
    if webSocket == controller_ws:
        controller_ws = None
    if webSocket == motors_ws:
        motors_ws = None

# ------------------------------------------------------------------------


def controller_websocket_join(webSocket):
    global controller_ws
    webSocket.OnTextMessage = controller_websocket_on_recv_text
    webSocket.OnClosed = websocket_on_close
    addr = webSocket.Request.UserAddress
    print('# Websocket join attempt from <%s:%s>' % addr)
    accepted = True
    with _wsLock:
        if controller_ws is None:
            controller_ws = webSocket
            controller_ws.SendTextMessage('# HELLO <%s:%s>' % addr)
        else:
            webSocket.SendTextMessage('# REJECTED <%s:%s>' % addr)
            controller_ws.SendTextMessage('# REJECTED <%s:%s>' % addr)
            webSocket.Close()
            accepted = False
    if accepted:
        print('# ACCEPTED <%s:%s>' % addr)
    else:
        print('# REJECTED <%s:%s>' % addr)


def motors_websocket_join(webSocket):
    global motors_ws
    webSocket.OnTextMessage = motors_websocket_on_recv_text
    webSocket.OnClosed = websocket_on_close
    addr = webSocket.Request.UserAddress
    print('# Websocket join attempt from <%s:%s>' % addr)
    accepted = True
    with _wsLock:
        if motors_ws is None:
            motors_ws = webSocket
            motors_ws.SendTextMessage('# HELLO <%s:%s>' % addr)
        else:
            webSocket.SendTextMessage('# REJECTED <%s:%s>' % addr)
            motors_ws.SendTextMessage('# REJECTED <%s:%s>' % addr)
            webSocket.Close()
            accepted = False
    if accepted:
        print('# ACCEPTED <%s:%s>' % addr)
    else:
        print('# REJECTED <%s:%s>' % addr)
# ------------------------------------------------------------------------


def controller_websocket_on_recv_text(webSocket, msg):
    json_data = json.loads(msg)
    cmd = None
    param = None
    if 'cmd' not in json_data:
        return
    if json_data['cmd'] not in robot.valid_cmd_dict:
        return
    cmd = robot.valid_cmd_dict[json_data['cmd']]
    param = None
    if 'param' in json_data:
        param = json_data['param']
        if param is not None:
            try:
                param = int(param)
            except OSError:
                pass
    robot.cmd_queue.append((cmd, param, webSocket))
    print('%s(%s)' % (cmd.__name__, str(param), ))


def motors_websocket_on_recv_text(webSocket, msg):
    global in1, in2, in3, in4
    json_data = json.loads(msg)
    if 'm1' not in json_data:
        return
    if 'm2' not in json_data:
        return
    motor1 = 0
    motor2 = 0
    try:
        motor1 = int(json_data['m1'])
        motor2 = int(json_data['m2'])
    except OSError:
        webSocket.Close()
        pass
    robot.set_motor_powers(motor1, motor2)
    # print('%s,%s' % (str(motor1), str(motor2)))


# ============================================================================
# ============================================================================
# ============================================================================


# Loads the WebSockets module globally and configure it,
wsMod = MicroWebSrv2.LoadModule('WebSockets')
wsMod.OnWebSocketAccepted = websocket_on_accept
mws2 = MicroWebSrv2()
mws2.SetEmbeddedConfig()
# All pages not found will be redirected to the home '/',
mws2.NotFoundURL = 'https://alpsayin.com'
mws2.StartManaged()
