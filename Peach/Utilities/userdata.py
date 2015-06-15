#!/usr/bin/env python
# TODO: uploading to s3 (with creds)
# TODO: detect deleted in s3 vs created locally
# TODO: detect/handle truncated listings > 1000 files/folder
import argparse
import calendar
import hashlib
from lxml import etree
import os
import subprocess as sp
import sys
import time
try:
    from urllib.request import urlopen, quote, urlencode
except ImportError:
    from urllib2 import urlopen, quote

import urllib


# these are regex
UPLOAD_EXCLUDES = [r'Thumbs\.db', r'__MACOSX', r'\.DS_Store']


class S3Object(object):

    def __init__(self):
        self.hash = None
        self.key = None
        self.size = None
        self.date = None

    def __str__(self):
        date = time.strftime("%b %d %Y %H:%M", time.localtime(self.date))
        return "%s %10d %18s %s" % (self.hash, self.size, date, self.key)

    def check(self):
        assert self.hash is not None
        assert self.key is not None
        assert self.size is not None
        assert self.date is not None


def list_bucket(bucket):
    remain = ['']
    while remain:
        prefix = remain.pop()
        params = urllib.urlencode({"delimiter": "/", "prefix":prefix})
        req = 'http://%s.s3.amazonaws.com/?%s' % (bucket, params)
        doc = etree.parse(urlopen(req))
        for element in doc.iter():
            tag = etree.QName(element).localname
            if tag == 'Prefix' and element.text is not None and element.text != prefix:
                remain.append(element.text)
            elif tag == 'Contents':
                result = S3Object()
                for child in element:
                    child_tag = etree.QName(child).localname
                    if child_tag == 'Key':
                        result.key = child.text
                    elif child_tag == 'ETag':
                        result.hash = child.text.strip('"')
                    elif child_tag == 'Size':
                        result.size = int(child.text)
                    elif child_tag == 'LastModified':
                        result.date = calendar.timegm(time.strptime(child.text, '%Y-%m-%dT%H:%M:%S.000Z'))
                result.check()
                yield result


def get_object(bucket, obj, file_path):
    if file_path.endswith("/"):
        return
    in_file = urlopen('http://%s.s3.amazonaws.com/%s' % (bucket, quote(obj.key)))
    size = int(in_file.info()['content-length'])
    assert size == obj.size
    folder = os.path.dirname(file_path)
    if not os.path.exists(folder):
        os.makedirs(folder)
    with open(file_path, 'wb') as out_file:
        while size > 0:
            buf = in_file.read(min(size, 64 * 1024))
            out_file.write(buf)
            size -= len(buf)
    os.utime(file_path, (obj.date, obj.date))


def download(bucket, obj, dry_run=False, folder_path='.'):
    local_path = os.path.join(folder_path, obj.key)
    dl = False
    if os.path.isfile(local_path):
        if os.stat(local_path).st_size != obj.size:
            dl = True
        else:
            local_hash = hashlib.md5()
            with open(local_path, 'rb') as existing:
                size = obj.size
                while size > 0:
                    buf = existing.read(min(size, 64 * 1024))
                    local_hash.update(buf)
                    size -= len(buf)
            if local_hash.hexdigest() != obj.hash:
                dl = True
        if dl:
            # size or hash differs, see if server is newer than local
            local_time = os.stat(local_path).st_mtime
            if obj.date < local_time:
                dl = False # local copy is newer .. don't clobber it
    else:
        dl = True
    if dl:
        if dry_run:
            print('download:', obj)
        else:
            get_object(bucket, obj, local_path)


def main():
    ap = argparse.ArgumentParser(description='Script to manage resources stored in S3',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    mx = ap.add_mutually_exclusive_group(required=True)
    mx.add_argument('-sync', action='store_true',
                    help='Sync resources in S3 (account not required)')
    mx.add_argument('-ls', action='store_true',
                    help='List resources in S3 (account not required)')
    mx.add_argument('-upload', action='store_true',
                    help='Upload resources using s3cmd (s3tools.org, account required)')
    ap.add_argument('-bucket', default='fuzzing.s3.mozilla.net',
                    help='Specify an alternate bucket')
    ap.add_argument('-folder', default='Resources',
                    help='Specify an alternate local folder')
    ap.add_argument('-dry-run', action='store_true',
                    help='Only show what would be up/downloaded')
    args = ap.parse_args()
    if args.sync:
        #local_pre = set()
        #in_s3 = set()
        #for (root, _, files) in os.walk(args.folder):
        #    local_pre |= {os.path.join(root, f) for f in files}
        for obj in list_bucket(args.bucket):
        #    in_s3.add(obj.key)
            download(args.bucket, obj, args.dry_run)
        #local_del = local_pre - in_s3
        #for f in local_del:
        #    os.unlink(f)
    elif args.ls:
        for obj in list_bucket(args.bucket):
            print(obj)
    elif args.upload:
        cmd = ['s3cmd', '--acl-public', 'sync', '%s/' % args.folder,
               's3://%s/%s/' % (args.bucket, args.folder)]
        for ex in UPLOAD_EXCLUDES:
            cmd.append('--rexclude=%s' % ex)
        if args.dry_run:
            cmd.append('--dry-run')
        res = sp.call(cmd)
        sys.exit(res)


if __name__ == '__main__':
    main()

