#!/usr/bin/env python3
import os, pty, select, subprocess, sys, time, signal

args = sys.argv[1:]
master, slave = pty.openpty()
p = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=slave, close_fds=True)
os.close(slave)
out = bytearray()
deadline = time.time() + int(os.environ.get('PI_PTY_TIMEOUT', '180'))
try:
    while True:
        if time.time() > deadline:
            p.kill(); raise TimeoutError('pi timed out')
        r, _, _ = select.select([master], [], [], 0.2)
        if master in r:
            try:
                b = os.read(master, 4096)
                if b: out.extend(b)
            except OSError:
                break
        if p.poll() is not None:
            time.sleep(0.1)
            try:
                while True:
                    b = os.read(master, 4096)
                    if not b: break
                    out.extend(b)
            except OSError:
                pass
            break
finally:
    try: os.close(master)
    except OSError: pass

text = out.decode(errors='replace').replace('\r\n', '\n').replace('\r', '\n')
text = text.replace('^D\b\b', '')
sys.stdout.write(text.strip() + ('\n' if text.strip() else ''))
sys.exit(p.returncode or 0)
