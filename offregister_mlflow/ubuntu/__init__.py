from __future__ import print_function

from platform import python_version_tuple

if python_version_tuple()[0] == "2":
    from cStringIO import StringIO
else:
    from io import StringIO

import offregister_circus.ubuntu as circus_mod
import offregister_nginx_static.ubuntu as nginx_static
import offregister_python.ubuntu as python_mod
from fabric.contrib.files import exists
from fabric.operations import put
from nginx_parse_emit.emit import api_proxy_block
from nginx_parse_emit.utils import merge_into, get_parsed_remote_conf
from nginxparser import loads, dumps
from offregister_fab_utils.ubuntu.systemd import restart_systemd


def install0(*args, **kwargs):
    kwargs.setdefault("virtual_env", "/opt/venvs/mlflow")

    if not kwargs.get("skip_virtualenv", False):
        venv0_kwargs = {
            "virtual_env": kwargs["virtual_env"],
            "python3": True,
            "pip_version": "19.2.3",
            "use_sudo": True,
            "remote_user": "ubuntu",
            "PACKAGES": ["mlflow[extras]"],
        }
        venv0_kwargs.update(kwargs)
        python_mod.install_venv0(**venv0_kwargs)

    circus0_kwargs = {
        "APP_NAME": "mlflow",
        "APP_PORT": 5000,
        "CMD": "{virtual_env}/bin/mlflow".format(virtual_env=kwargs["virtual_env"]),
        "CMD_ARGS": "ui",
        "WSGI_FILE": None,
    }
    circus0_kwargs.update(kwargs)
    circus_mod.install_circus0(**circus0_kwargs)

    kwargs.setdefault("skip_nginx_restart", True)
    kwargs.setdefault(
        "conf_remote_filename",
        "/etc/nginx/sites-enabled/{}.conf".format(kwargs["SERVER_NAME"]),
    )
    kwargs.update(
        {
            "nginx_conf": "proxy-pass.conf",
            "NAME_OF_BLOCK": "mlflow",
            "SERVER_LOCATION": "localhost:{port}".format(
                port=circus0_kwargs["APP_PORT"]
            ),
            "LISTEN_PORT": 80,
            "LOCATION": "/",
        }
    )
    if exists(kwargs["conf_remote_filename"]):
        parsed_remote_conf = get_parsed_remote_conf(kwargs["conf_remote_filename"])

        parsed_api_block = loads(
            api_proxy_block(
                location=kwargs["LOCATION"],
                proxy_pass="http://{}".format(kwargs["SERVER_LOCATION"]),
            )
        )
        sio = StringIO()
        sio.write(
            dumps(
                merge_into(kwargs["SERVER_NAME"], parsed_remote_conf, parsed_api_block)
            )
        )
        sio.seek(0)

        put(sio, kwargs["conf_remote_filename"], use_sudo=True)
    else:
        nginx_static.setup_conf0(**kwargs)

        # with shell_env(VIRTUAL_ENV=kwargs['virtual_env'], PATH="{}/bin:$PATH".format(kwargs['virtual_env'])):sudo('mlflow initdb')

    restart_systemd("circusd")
