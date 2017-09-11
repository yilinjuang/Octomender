from enum import Enum

import paramiko

from app import app

class Status(Enum):
    WAITING = 1
    RUNNING = 2
    RECVING = 3
    FAILED = 4
    END = 5

class Octomender(object):
    REMOTE_URL = <REMOTE-URL>

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

    def __init__(self, uid, token):
        self.uid = uid
        self.token = token
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.client.connect(Octomender.REMOTE_URL)

    @staticmethod
    def _buf_line(f):
        buffer = ''
        while not f.channel.exit_status_ready() or f.channel.recv_ready():
            buffer += f.read(1).decode('utf-8')
            if buffer.endswith('\n'):
                yield buffer
                buffer = ''

    def exec_remote(self):
        command = 'cd ~/octomender/;'
        command += 'python octomender.py {} {};'.format(self.uid, self.token)
        _, self.stdout, _ = self.client.exec_command(command)

    def sync_remote(self):
        repos = []
        progress = 0
        full_progress = 100
        status = Status.RUNNING
        for line in Octomender._buf_line(self.stdout):
            assert status != Status.FAILED and status != Status.END
            line = line[:-1]  # Remove trailing \n.
            log = 'sync_remote: |{}| '.format(line)
            if line == '.':
                log += 'progress report'
                assert status == Status.RUNNING
                progress += 1
                yield progress / full_progress * 100
            elif line.startswith('R'):
                log += 'repo received'
                assert status == Status.WAITING or status == Status.RECVING
                status = Status.RECVING
                repos.append(int(line[1:]))
            elif line.startswith('N'):
                log += 'full progress received'
                assert status == Status.RUNNING
                full_progress = int(line[1:])
            elif line == 'D':
                log += 'done running'
                assert progress == full_progress
                assert status == Status.RUNNING
                status = Status.WAITING
            elif line == 'E':
                log += 'end'
                assert status == Status.RECVING
                status = Status.END
            elif line == 'V':
                log += 'no valid repos'
                assert status == Status.RUNNING
                status = Status.FAILED
                yield "octomender can't find enough stars of you in the sky"
            elif line == 'F':
                log += 'calulation failed'
                assert status == Status.WAITING
                status = Status.FAILED
                yield 'octomender caught a cold'
            else:
                log += 'unrecognized sync message'
            app.logger.debug(log)
        yield repos  # return repos.
