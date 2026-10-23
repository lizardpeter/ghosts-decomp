#!/usr/bin/env python3
"""Stage original MP startup FastFiles; preserve paths and verify source fingerprints.

The authored inventory pins size and the plain MD5 ETag from the owner's R2
objects. Record independently computed SHA-256 for every acquired local file.
This is the core/UI subset, not a complete map or game installation.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
PREFIX='ghosts/DUMP/'


def fingerprints(path):
    md5,sha=hashlib.md5(),hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(1<<20):
            md5.update(block)
            sha.update(block)
    return md5.hexdigest(),sha.hexdigest()


def fetch(row,output):
    key=row['key']
    if not key.startswith(PREFIX):
        raise ValueError('Unexpected source prefix')
    name=key[len(PREFIX):]
    if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or not re.fullmatch(r'[A-Za-z0-9_/]+\.ff',name):
        raise ValueError('Unsafe source path')
    size=int(row['size'])
    if size<=0 or not re.fullmatch(r'[0-9a-f]{32}',row['md5']):
        raise ValueError('Invalid source fingerprint')
    path=output/name
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.stat().st_size==size:
        md5,sha=fingerprints(path)
        if md5==row['md5']:
            return {'key':key,'size':size,'md5':md5,'sha256':sha,'reused':True}
    temp=path.with_suffix('.ff.partial')
    try:
        subprocess.run(['curl','--fail','--location','--silent','--show-error',
                        '--retry','3','--connect-timeout','20','--max-time','300',
                        'https://r2.houseofkublai.com/'+key,'--output',str(temp)],check=True)
        md5,sha=fingerprints(temp)
        if temp.stat().st_size!=size or md5!=row['md5']:
            raise ValueError('Original size/MD5 mismatch: '+key)
        temp.replace(path)
        return {'key':key,'size':size,'md5':md5,'sha256':sha,'reused':False}
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path,default=ROOT/'records/native-startup-sources.tsv')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    rows=list(csv.DictReader(args.inventory.open(),delimiter='\t'))
    if len({r['key'] for r in rows})!=len(rows):
        raise ValueError('Duplicate source keys')
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(lambda row:fetch(row,args.output),rows):
            results.append(result)
            print(result['key'],result['size'],result['sha256'],flush=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({'files':results,'complete_game_installation':False},indent=2)+'\n')


if __name__=='__main__':
    main()
