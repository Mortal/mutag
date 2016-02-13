#!/usr/bin/env python3
import os
import shlex
import shutil
import argparse
import tempfile
import textwrap
import subprocess
import collections

import mutagen.easyid3
import mutagen.easymp4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--no-backup', dest='backup',
                        action='store_false')
    parser.add_argument('filename')
    args = parser.parse_args()

    keys = 'artist album title tracknumber discnumber date'.split()

    ext = os.path.splitext(args.filename)[1]
    if ext == '.mp3':
        t = mutagen.easyid3.EasyID3(args.filename)
    elif ext == '.m4a':
        t = mutagen.easymp4.EasyMP4(args.filename)
    else:
        parser.error("Unknown extension %s" % shlex.quote(ext))

    tags = collections.OrderedDict([(k, '') for k in keys])
    for k, v in t.items():
        tags[k] = ', '.join(v)

    with tempfile.NamedTemporaryFile(mode='w+') as fp:
        for k, v in tags.items():
            fp.write('%s ' % k)
            fp.write(' '.join(shlex.quote(s) for s in v.split()))
            fp.write('\n')
        fp.write(textwrap.dedent("""\
        # Each line will be written to the file
        # Deleting a line will leave the tag unchanged
        # Original filename was %s
        """ % shlex.quote(args.filename)))
        fp.flush()
        returncode = subprocess.call(('vim', fp.name))
        if returncode != 0:
            raise SystemExit(
                "Editor returned %s; quitting" % returncode)
        fp.seek(0)
        s = fp.read()
    lines = 0
    for l in s.splitlines():
        if l.startswith('#'):
            continue
        p = shlex.split(l)
        key = p[0]
        if key.startswith('#'):
            continue
        lines += 1
        value = ' '.join(p[1:])
        if not value:
            t.pop(key, None)
        else:
            t[key] = [value]
    if not lines:
        raise SystemExit(
            "No lines in buffer; quitting")
    if args.backup:
        backupname = args.filename + '~'
        if os.path.exists(backupname):
            print("Not overwriting existing backup %s" %
                  shlex.quote(backupname))
        else:
            print("Copying file to %s" % shlex.quote(backupname))
            shutil.copyfile(args.filename, backupname)
            shutil.copystat(args.filename, backupname)
    print("Saving file with mutagen")
    t.save()


if __name__ == "__main__":
    main()
