#!/usr/bin/python2
# coding: utf-8
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

import os
import re
import xml.etree.cElementTree as ET
import glob
import gzip
import argparse
import urllib
import urlparse


class Package(object):
    def __init__(self):
        self.name = None
        self.version = None
        self.release = None
        self.epoch = None
        self.location = None

    def __str__(self):
        return ' '.join([self.name, self.version, self.release, self.location])

def parse_primary(filepath):
    if filepath.endswith('gz'):
        fobj = gzip.open(filepath, 'rb')
        root = ET.fromstring(fobj.read())
        fobj.close()
    else:
        etree = ET.parse(filepath)
        root = etree.getroot()
    xmlns = re.sub('metadata$', '', root.tag)
    packages = {}
    for item in root.findall(xmlns + 'package'):
        pkg = Package()
        name = item.find(xmlns + 'name').text
        ver = dict(item.find(xmlns + 'version').items())
        pkg.name = name
        pkg.version = ver['ver']
        pkg.release = ver['rel']
        pkg.epoch = ver['epoch']
        pkg.location = item.find(xmlns + 'location').attrib['href']
        packages[name] = pkg
    return packages

def parse_repomd(baseurl):
    if not baseurl.endswith('/'):
        baseurl += '/'
    repomd_url = urlparse.urljoin(baseurl, 'repodata/repomd.xml')
    fobj = urllib.urlopen(repomd_url)
    root = ET.fromstring(fobj.read())
    xmlns = re.sub('repomd$', '', root.tag)
    for item in root.findall(xmlns + 'data'):
        if item.get('type') == 'primary':
            return urlparse.urljoin(
                    baseurl,
                    item.find(xmlns + 'location').get('href')
                    )

def parse_args():
    """ parse arguments """
    parser = argparse.ArgumentParser(description='Update prebuilt packages')
    parser.add_argument('-R', '--remote-repo', required=True, help='remote repo url containing repodata directory')
    parser.add_argument('-L', '--local-repo', required=True, help='local repo url containing repodata directory')

    return  parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    primary_url = parse_repomd(args.remote_repo)
    urllib.urlretrieve(primary_url, 'primary.xml.gz')
    remote_packages = parse_primary('primary.xml.gz')
    prebuilt = args.local_repo

    if not os.path.exists(os.path.join(prebuilt, 'repodata/repomd.xml')):
        print "local prebuilt must be a rpm repp with repodata dir exists"
        exit(2)

    primary_file = glob.glob(os.path.join(prebuilt, 'repodata/*primary.xml.gz'))[0]

    # Clean up old RPMs
    for pkg in glob.glob(os.path.join(prebuilt, '*.rpm')):
        os.system("git rm %s" % pkg)

    for pkgname, pkgobj in parse_primary(primary_file).items():
        pkgurl = args.remote_repo + '/' + remote_packages[pkgname].location
        print "downloading", pkgname
        try:
           urllib.urlretrieve(pkgurl, os.path.join(prebuilt, os.path.basename(remote_packages[pkgname].location)))
        except:
           print "failed to download", pkgurl, ", please download it manually"

    # Update repodata
    os.unlink("primary.xml.gz")
    os.system("git rm -r repodata")
    os.system("createrepo %s" % prebuilt)
