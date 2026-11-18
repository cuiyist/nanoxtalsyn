"""S3 release sizes: count exact published manifest bytes, no anonymous bodies."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath


def release_sizes(manifest, source_size_kib, site_size_kib):
    if not all(type(n) is int and n >= 0 for n in (source_size_kib,site_size_kib)):
        raise ValueError('Exact GitHub repository size fields required')
    files = {}
    for row in manifest['files']:
        path,size = row['path'],row['bytes']
        if (not isinstance(path,str) or not path or '\\' in path or
            PurePosixPath(path).is_absolute() or any(part in ('','.','..') for part in path.split('/')) or
            type(size) is not int or size < 0 or path in files):
            raise ValueError('Invalid or repeated publish manifest path/size')
        files[path] = size
    if not files: raise ValueError('Cannot report an empty deployment')
    ordered = sorted(files.items(),key=lambda row:(-row[1],row[0]))
    row = lambda entry:{'path':entry[0],'bytes':entry[1]}
    return {'source_commit':manifest['source_commit'],'site_file_count':len(files),
            'site_bytes':sum(files.values()),
            'paper_review_asset_bytes':sum(size for path,size in ordered if path.startswith('assets/paper-reviews/')),
            'largest_published_files':[row(entry) for entry in ordered[:5]],
            'files_over_70_mb':[row(entry) for entry in ordered if entry[1]>70_000_000],
            'github_repo_size_kib':{'source':source_size_kib,'site':site_size_kib},
            'basis':'Built Site allowlist (served files, excluding repository control files); GitHub repository size API reports KiB.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('work',type=Path)
    parser.add_argument('--source-kib',type=int,required=True)
    parser.add_argument('--site-kib',type=int,required=True)
    args = parser.parse_args()
    load = lambda name:json.loads((args.work/name).read_bytes())
    push = load('push.json')
    if push.get('pushed') is not True:
        print('No deployment to measure.')
        return
    build,stage,live = (load(p) for p in ('build.json','stage.json','receipts/live-verification.json'))
    brand = load('receipts/n-brand-published-scan.json')
    source,site = push['source_commit'],push['site_commit']
    manifest_bytes=(args.work/'site-allowlist.json').read_bytes()
    manifest=json.loads(manifest_bytes)
    if (not all(x['source_commit']==source for x in (build,stage,live,brand,manifest)) or
        not live.get('passed') or not live.get('anonymous') or not brand.get('passed') or
        brand.get('site_commit')!=site or hashlib.sha256(manifest_bytes).hexdigest()!=build['allowlist_sha256']):
        raise ValueError('Published size inventory needs the exact verified deployment and manifest')
    result=release_sizes(manifest,args.source_kib,args.site_kib)
    result['site_commit']=site
    with (args.work/'receipts/site-size.json').open('x',encoding='utf-8',newline='\n') as f:
        json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
    high=result['files_over_70_mb']
    lines = ['## Published Site inventory']
    if high: lines.append(f'**Warning: {len(high)} published file(s) exceed 70 MB.**')
    lines.append(f"{result['site_file_count']:,} files, {result['site_bytes']:,} bytes. "
                 f"Paper-review assets: {result['paper_review_asset_bytes']:,} bytes.")
    lines.append(f"GitHub repository sizes: Source {args.source_kib:,} KiB; Site {args.site_kib:,} KiB.")
    for row in result['largest_published_files']:
        name=row['path'].replace('`','').replace('\n','').replace('\r','')
        lines.append(f"- `{name}`: {row['bytes']:,} bytes")
    summary='\n'.join(lines)+'\n'
    print(summary,end='')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f: f.write(summary)


if __name__=='__main__':
    main()
