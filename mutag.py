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


def load_file(filename, parser, args):
    ext = os.path.splitext(filename)[1]
    if ext == '.mp3':
        t = mutagen.easyid3.EasyID3(filename)
    elif ext == '.m4a':
        t = mutagen.easymp4.EasyMP4(filename)
    else:
        parser.error("Unknown extension %s" % shlex.quote(ext))

    keys = args.keys
    tags = collections.OrderedDict([(k, '') for k in keys])
    for k, v in t.items():
        tags[k] = ', '.join(v)

    return filename, (t, tags)


def escape(v):
    return ' '.join(shlex.quote(s) for s in v.split())


def main():
    def_keys = 'artist album title tracknumber discnumber date'.split()
    short_keys = 'artist title'.split()

    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--backup', dest='backup',
                        action='store_true')
    parser.add_argument('-s', '--short', dest='keys',
                        action='store_const', const=short_keys,
                        default=def_keys)
    parser.add_argument('filename', nargs='+')
    args = parser.parse_args()

    files = collections.OrderedDict(
        [load_file(filename, parser, args)
         for filename in args.filename])

    with tempfile.NamedTemporaryFile(mode='w+') as fp:
        for filename, (tagger, tags) in files.items():
            fp.write('filename %s\n' % (escape(filename),))
            for k, v in tags.items():
                fp.write('%s %s\n' % (k, escape(v)))
            fp.write('\n')
        fp.write(textwrap.dedent("""\
        # Each line will be written to the file
        # Deleting a line will leave the tag unchanged
        """))
        fp.flush()
        returncode = subprocess.call(('vim', fp.name))
        if returncode != 0:
            raise SystemExit(
                "Editor returned %s; quitting" % returncode)
        fp.seek(0)
        s = fp.read()
    lines = {filename: 0 for filename in files.keys()}
    current_file = None
    for l in s.splitlines():
        if l.startswith('#'):
            continue
        p = shlex.split(l)
        if not p:
            continue
        key = p[0]
        if key.startswith('#'):
            continue
        value = ' '.join(p[1:])
        if key == 'filename':
            current_file = value
            continue
        lines[current_file] += 1
        if not value:
            files[current_file][0].pop(key, None)
        else:
            files[current_file][0][key] = [value]

    for filename, (t, tags) in files.items():
        if not lines[filename]:
            print("%s: No lines in buffer" % shlex.quote(filename))
            continue
        if args.backup:
            backupname = filename + '~'
            if os.path.exists(backupname):
                print("%s: Not overwriting existing backup %s" %
                      (shlex.quote(filename), shlex.quote(backupname)))
            else:
                print("Copying %s to %s" %
                      (shlex.quote(filename), shlex.quote(backupname)))
                shutil.copyfile(filename, backupname)
                shutil.copystat(filename, backupname)
        print("Saving %s with mutagen" % shlex.quote(filename))
        t.save()


if __name__ == "__main__":
    main()
