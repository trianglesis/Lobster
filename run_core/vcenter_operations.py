import os
import logging
import atexit
import ssl
# noinspection PyUnresolvedReferences
from pyVim import connect
# noinspection PyUnresolvedReferences
from pyVmomi import vim

from octo.config_cred import v_center_cred

log = logging.getLogger("octo.octologger")
place = os.path.dirname(os.path.abspath(__file__))


class VCenterOper:
    """

    """


# noinspection PyUnusedLocal
def vconnect():
    s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    s.verify_mode = ssl.CERT_NONE  # disable our certificate checking for lab

    service_instance = connect.SmartConnect(
        host=v_center_cred['host_vc'],
        user=v_center_cred['VC_USER'],
        pwd=v_center_cred['VC_PWD'],
        sslContext=s)

    atexit.register(connect.Disconnect, service_instance)  # build disconnect logic

    content = service_instance.RetrieveContent()

    container = content.rootFolder  # starting point to look into
    viewType = [vim.VirtualMachine]  # object types to look for
    recursive = True  # whether we should look into it recursively
    containerView = content.viewManager.CreateContainerView(container, viewType, recursive)  # create container view
