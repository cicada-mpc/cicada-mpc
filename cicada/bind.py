# Copyright 2021 National Technology & Engineering Solutions
# of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS,
# the U.S. Government retains certain rights in this software.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Functionality for binding to network interfaces."""

import contextlib
import logging
import socket

import netifaces

log = logging.getLogger()

def loopback_ip():
    """Return an IP address for localhost."""
    return "127.0.0.1"


def public_ip():
    """Return a public-facing IP address."""
    gateway, interface = netifaces.gateways()["default"][netifaces.AF_INET]
    return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]


def random_port(addr):
    """Return a randomly-chosen open port number for the given address."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((addr, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

