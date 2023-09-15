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

"""Provides a command line interface for running Cicada programs.
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import tempfile
import urllib.parse

import netifaces
import numpy

import cicada
from cicada.additive import AdditiveProtocolSuite
from cicada.communicator import SocketCommunicator
from cicada.communicator.socket.connect import geturl
from cicada.logging import Logger


def get_environment(world_size, rank, address, root_address, identity, trusted):
    env = {
        "CICADA_WORLD_SIZE": str(world_size),
        "CICADA_RANK": str(rank),
        "CICADA_ADDRESS": address,
        "CICADA_ROOT_ADDRESS": root_address,
    }

    if identity:
        env["CICADA_IDENTITY"] = identity
    if trusted:
        env["CICADA_TRUSTED"] = ",".join(trusted)

    return env


def log_command(command, env, log):
    log.info(f"Command: {' '.join(command)}")
    log.info(f"  Environment:")
    for key, value in env.items():
        if key.startswith("CICADA_"):
            log.info(f"    {key}={value}")


def public_ip():
    """Return a public-facing IP address."""
    gateway, interface = netifaces.gateways()["default"][netifaces.AF_INET]
    return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]


def basic_frontend(arguments, players, log):
    processes = []
    for world_size, rank, address, root_address, identity, trusted in players:
        env = os.environ.copy()
        env.update(get_environment(world_size, rank, address, root_address, identity, trusted))

        command = [sys.executable]
        if arguments.inspect:
            command += ["-i"]
        command += [arguments.program]
        command += arguments.args

        log_command(command, env, log)

        if not arguments.dry_run:
            processes.append(subprocess.Popen(command, env=env))

    if not arguments.dry_run:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for process in processes:
            process.wait()


def tmux_panes_frontend(arguments, players, log):
    command = []
    for world_size, rank, address, root_address, identity, trusted in players:
        env = get_environment(world_size, rank, address, root_address, identity, trusted)

        if rank == 0:
            command += ["tmux", "new-session"]
        else:
            command += [";", "split-window", "-v", "-d"]

        for name, value in env.items():
            command += ["-e", f"{name}={value}"]
        command += [sys.executable]
        if arguments.inspect:
            command += ["-i"]
        command += [arguments.program]
        command += arguments.args

    command += [";", "select-layout", arguments.tmux_layout]

    log.info(f"Command: {' '.join(command)}")

    processes = []
    if not arguments.dry_run:
        processes.append(subprocess.Popen(command))

    if not arguments.dry_run:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for process in processes:
            process.wait()


def tmux_windows_frontend(arguments, players, log):
    command = []
    for world_size, rank, address, root_address, identity, trusted in players:
        env = get_environment(world_size, rank, address, root_address, identity, trusted)

        if rank == 0:
            command += ["tmux", "new-session"]
        else:
            command += [";", "new-window", "-d"]

        command += ["-n", f"rank-{rank}"]
        for name, value in env.items():
            command += ["-e", f"{name}={value}"]
        command += [sys.executable]
        if arguments.inspect:
            command += ["-i"]
        command += [arguments.program]
        command += arguments.args

    log.info(f"Command: {' '.join(command)}")

    processes = []
    if not arguments.dry_run:
        processes.append(subprocess.Popen(command))

    if not arguments.dry_run:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for process in processes:
            process.wait()


def xterm_frontend(arguments, players, log):
    processes = []
    for world_size, rank, address, root_address, identity, trusted in players:
        env = os.environ.copy()
        env.update(get_environment(world_size, rank, address, root_address, identity, trusted))

        command = ["xterm", "-e"]
        command += [sys.executable]
        if arguments.inspect:
            command += ["-i"]
        command += [arguments.program]
        command += arguments.args

        log_command(command, env, log)

        if not arguments.dry_run:
            processes.append(subprocess.Popen(command, env=env))

    if not arguments.dry_run:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for process in processes:
            process.wait()


frontends = {
    "basic": basic_frontend,
    "tmux": tmux_panes_frontend,
    "tmux-windows": tmux_windows_frontend,
    "xterm": xterm_frontend,
}


parser = argparse.ArgumentParser(description="Cicada MPC tools.")
subparsers = parser.add_subparsers(title="commands (choose one)", dest="command")

# certificate-info
certificate_info_subparser = subparsers.add_parser("certificate-info", help="Display information about a TLS certificate.")
certificate_info_subparser.add_argument("path", help="Path to the certificate file.")

# credentials
credentials_subparser = subparsers.add_parser("credentials", help="Generate player credentials for TLS encryption.")
credentials_subparser.add_argument("--certificate", default="player-{rank}.cert", help="Output certificate file. Default: %(default)s")
credentials_subparser.add_argument("--country", default="US", help="Certificate country. Default: %(default)s")
credentials_subparser.add_argument("--days", type=int, default=365, help="Length of time the certificate will be valid. Default: %(default)s")
credentials_subparser.add_argument("--email", default=None, help="Certificate email. Default: %(default)s")
credentials_subparser.add_argument("--identity", default="player-{rank}.pem", help="Output identity (private key and certificate) file. Default: %(default)s")
credentials_subparser.add_argument("--locality", default="Albuquerque", help="Certificate locality. Default: %(default)s")
credentials_subparser.add_argument("--name", default=None, help="Common name. Default: based on player rank.")
credentials_subparser.add_argument("--organization", default="Cicada", help="Certificate organization. Default: %(default)s")
credentials_subparser.add_argument("--rank", required=True, help="Player rank.")
credentials_subparser.add_argument("--state", default="New Mexico", help="Certificate state. Default: %(default)s")
credentials_subparser.add_argument("--unit", default=None, help="Certificate organizational unit. Default: %(default)s")

# generate-shares
generate_subparser = subparsers.add_parser("generate-shares", help="Generate secret shares for pedagogy.")
generate_subparser.add_argument("--order", "-m", type=int, default=18446744073709551557, help="Field modulus. Default: %(default)s")
generate_subparser.add_argument("--precision", "-p", type=int, default=16, help="Fractional precision. Default: %(default)s")
generate_subparser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")
generate_subparser.add_argument("secret", help="Secret value.")

# run
run_subparser = subparsers.add_parser("run", help="Run all Cicada processes on the local machine.")
run_subparser.add_argument("--dry-run", "-y", action="store_true", help="Don't start actual processes.")
run_subparser.add_argument("--frontend", "-f", choices=frontends.keys(), default="basic", help="Frontend to execute processes.")
run_subparser.add_argument("--identity", default="player-{rank}.pem", help="Player private key and certificate in PEM format. Default: %(default)s file, if it exists.")
run_subparser.add_argument("--inspect", "-i", action="store_true", help="Start a Python prompt after running program.")
run_subparser.add_argument("--trusted", default="player-{rank}.cert", help="Trusted certificates in PEM format. Default: %(default)s files, if they exist.")
run_subparser.add_argument("--root-address", default="tcp://127.0.0.1:25252", help="Root address.  Default: %(default)s")
run_subparser.add_argument("--tmux-layout", default="even-vertical", choices=["even-horizontal", "even-vertical", "tiled"], help="Pane layout for the tmux frontend. Default: %(default)s")
run_subparser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")
run_subparser.add_argument("program", help="Program to execute.")
run_subparser.add_argument("args", nargs=argparse.REMAINDER, help="Program arguments.")

# start
start_subparser = subparsers.add_parser("start", help="Start one Cicada process.")
start_subparser.add_argument("--dry-run", "-y", action="store_true", help="Don't start actual processes.")
start_subparser.add_argument("--address", default=None, help=f"Network address. Default: tcp://{public_ip()}:25252 for player 0, otherwise tcp://{public_ip()}")
start_subparser.add_argument("--identity", default="player-{rank}.pem", help="Player private key and certificate in PEM format. Default: %(default)s file, if it exists.")
start_subparser.add_argument("--inspect", "-i", action="store_true", help="Start a Python prompt after running program.")
start_subparser.add_argument("--trusted", default="player-{rank}.cert", help="Trusted certificates in PEM format. Default: %(default)s files, if they exist.")
start_subparser.add_argument("--root-address", default=None, help="Root address. Default: same as --address for player 0, required otherwise.")
start_subparser.add_argument("--rank", type=int, required=True, help="Player rank.")
start_subparser.add_argument("--world-size", "-n", type=int, default=3, help="Number of players. Default: %(default)s")
start_subparser.add_argument("program", help="Program to execute.")
start_subparser.add_argument("args", nargs=argparse.REMAINDER, help="Program arguments.")

# version
version_subparser = subparsers.add_parser("version", help="Print the Cicada version.")


def main():
    arguments = parser.parse_args()

    if arguments.command is None:
        parser.print_help()

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger()
    log.name = os.path.basename(sys.argv[0])


    # certificate-info
    if arguments.command == "certificate-info":
        subprocess.run(["openssl", "x509", "-in", arguments.path, "-text"], check=True)

    # credentials
    if arguments.command == "credentials":
        rank = arguments.rank

        if arguments.name is None:
            arguments.name = f"Player {rank}"

        subj = ""
        subj += f"/C={arguments.country}" if arguments.country else ""
        subj += f"/ST={arguments.state}" if arguments.state else ""
        subj += f"/L={arguments.locality}" if arguments.locality else ""
        subj += f"/O={arguments.organization}" if arguments.organization else ""
        subj += f"/OU={arguments.unit}" if arguments.unit else ""
        subj += f"/emailAddress={arguments.email}" if arguments.email else ""
        subj += f"/CN={arguments.name}"

        certificate_path = arguments.certificate.format(rank=rank)
        identity_path = arguments.identity.format(rank=rank)

        fd, key_path = tempfile.mkstemp()
        os.close(fd)

        subprocess.check_call(["openssl", "genrsa", "-out", key_path, "2048"])
        subprocess.check_call(["openssl", "req", "-new", "-key", key_path, "-x509", "-subj", subj, "-out", certificate_path, "-days", str(arguments.days)])
        with open(identity_path, "wb") as target:
            with open(key_path, "rb") as source:
                target.write(source.read())
            with open(certificate_path, "rb") as source:
                target.write(source.read())
        os.remove(key_path)

    # generate-shares
    if arguments.command == "generate-shares":
        logging.basicConfig(level=logging.INFO)

        def main(communicator, precision, order, secret):
            log = Logger(logging.getLogger(), communicator)

            protocol = AdditiveProtocolSuite(communicator, order=order, encoding=cicada.encoding.FixedPoint(precision=precision))
            secret = numpy.array(secret, dtype=float)
            share = protocol.share(src=0, secret=secret, shape=secret.shape)

            log.info(f"Player {communicator.rank} secret share: {share.storage}")

        SocketCommunicator.run(world_size=arguments.world_size, fn=main, args=(arguments.precision, arguments.order, arguments.secret))

    # run
    if arguments.command == "run":
        world_size = arguments.world_size
        if world_size < 1:
            run_subparser.error("--world-size must be greater than zero.")

        root_address = urllib.parse.urlparse(arguments.root_address)
        if root_address.scheme not in ["file", "tcp"]:
            run_subparser.error(f"--root-address scheme must be file or tcp, got {root_address.scheme} instead.")
        if root_address.scheme == "tcp" and root_address.port is None:
            run_subparser.error("--root-address must specify a port number when the scheme is tcp.")

        addresses = []
        for rank in range(world_size):
            if rank == 0:
                addresses.append(arguments.root_address)
            else:
                if root_address.scheme == "file":
                    fd, path = tempfile.mkstemp()
                    os.close(fd)
                    addresses.append(f"file://{path}")
                if root_address.scheme == "tcp":
                    addresses.append(f"tcp://{root_address.hostname}")

        players = []
        for rank, address in enumerate(addresses):
            identity = arguments.identity.format(rank=rank, world_size=world_size)
            if not os.path.exists(identity):
                identity = ""

            trusted = []
            for index in range(world_size):
                trust = arguments.trusted.format(rank=index, world_size=world_size)
                if index != rank and os.path.exists(trust):
                    trusted.append(trust)

            players.append((world_size, rank, address, addresses[0], identity, trusted))

        frontend = frontends[arguments.frontend]
        frontend(arguments, players, log)

    # start
    if arguments.command == "start":
        world_size = arguments.world_size
        if world_size < 1:
            start_subparser.error("--world-size must be greater than zero.")

        rank = arguments.rank
        if rank < 0 or rank >= world_size:
            start_subparser.error(f"--rank must be in the range [0, {world_size}).")

        address = arguments.address
        if address is None:
            address = f"tcp://{public_ip()}:25252" if rank == 0 else f"tcp://{public_ip()}"
        address = urllib.parse.urlparse(address)
        address = address.geturl()

        root_address = arguments.root_address
        if root_address is None:
            if rank == 0:
                root_address = address
            else:
                start_subparser.error(f"--root-address must be specified.")
        root_address = urllib.parse.urlparse(root_address)
        root_address = root_address.geturl()

        identity = arguments.identity.format(rank=rank, world_size=world_size)
        if not os.path.exists(identity):
            identity = ""

        trusted = []
        for index in range(world_size):
            trust = arguments.trusted.format(rank=index, world_size=world_size)
            if index != rank and os.path.exists(trust):
                trusted.append(trust)

        players = [(world_size, rank, address, root_address, identity, trusted)]
        frontend = frontends["basic"]
        frontend(arguments, players, log)

    # version
    if arguments.command == "version":
        print(cicada.__version__)


