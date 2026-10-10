"""Preserve release support bytes in one archive; never replace installers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def checksum_entries(text):
    entries={}
    for line in text.splitlines():
        digest,name=line.split("  ",1)
        if not re.fullmatch(r"[0-9a-f]{64}",digest) or name in entries:
            raise ValueError("Invalid or duplicate hash")
        if Path(name).name!=name or name in (".","..") or "/" in name or "\\" in name:
            raise ValueError("Unsafe asset name")
        entries[name]=digest
    return entries

def installer_names(version):
    return {f"SlideExtractor-v{version}-macOS-arm64.dmg",
            f"SlideExtractor-v{version}-Setup-Windows-x64.exe"}

def bundle_name(version):
    return f"SlideExtractor-v{version}-Sources-Licenses.zip"

def compact_assets(root,output,version,documentation=None):
    root,output=Path(root),Path(output)
    if not re.fullmatch(r"0\.[0-9]+\.[0-9]+(?:rc[0-9]+)?",version):
        raise ValueError("Invalid version")
    entries=checksum_entries((root/"SHA256SUMS.txt").read_text())
    paths={p.name:p for p in root.iterdir()}
    if set(paths)!=set(entries)|{"SHA256SUMS.txt"}:
        raise ValueError("Asset inventory differs from checksums")
    if not installer_names(version)<=set(entries):
        raise ValueError("Installer inventory incomplete")
    for name,digest in entries.items():
        if paths[name].is_symlink() or not paths[name].is_file() or sha256(paths[name])!=digest:
            raise ValueError("Asset hash mismatch: "+name)
    output.mkdir()
    archive=output/bundle_name(version)
    # Upstream archives are already compressed; avoid a second expensive compression.
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_STORED,allowZip64=True) as z:
        for name in sorted(set(entries)-installer_names(version)):
            z.write(paths[name],name)
        z.write(root/"SHA256SUMS.txt","ORIGINAL-SHA256SUMS.txt")
        z.writestr("README.txt",
            "Slide Extractor "+version+" — sources, licenses and verification\n\n"
            "For installation download only the macOS DMG or Windows Setup EXE.\n"
            "This archive preserves the original corresponding source archives,\n"
            "OpenCV patches, FFmpeg build inputs, license notices and audit evidence.\n"
            "ORIGINAL-SHA256SUMS.txt records hashes of the original release files;\n"
            "installer files are provided separately with unchanged hashes.\n"
            "build-and-review-evidence.zip contains both OS license copies, build\n"
            "settings, SBOMs and final license-audit/audit-report.json records.\n"
            "docs/SOURCE_AND_REPLACEMENT.md explains LGPL library replacement.\n"
            "GitHub's automatic Source code downloads contain only app repository\n"
            "sources, not the third-party corresponding sources supplied here.\n")
        if documentation:
            for path in documentation:
                path=Path(path)
                z.write(path,"docs/"+path.name)
    # Re-read every original support entry before permitting publication/cleanup.
    with zipfile.ZipFile(archive) as z:
        for name in sorted(set(entries)-installer_names(version)):
            with z.open(name) as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=entries[name]:
                    raise ValueError("Archive hash mismatch: "+name)
    for name in installer_names(version):
        shutil.copy2(paths[name],output/name)
    (output/"SHA256SUMS.txt").write_text("".join(
        f"{sha256(path)}  {path.name}\n" for path in sorted(output.iterdir())))

def gh(*args):
    return subprocess.check_output(["gh",*map(str,args)],text=True)

def release(repo,tag):
    return json.loads(gh("api",f"repos/{repo}/releases/tags/{tag}"))

def migrate(config_path):
    c=json.loads(Path(config_path).read_text())
    repo=os.environ["GITHUB_REPOSITORY"]
    tag=c["tag"]
    original={a["name"]:a for a in c["assets"]}
    installers=installer_names(c["version"])
    bundle=bundle_name(c["version"])
    r=release(repo,tag)
    if r["id"]!=c["release_id"] or r["draft"]:
        raise ValueError("Unexpected release identity")
    current={a["name"]:a for a in r["assets"]}
    if not set(current)<=set(original)|{bundle}:
        raise ValueError("Unexpected public asset inventory")
    for name in installers:
        if current[name]["digest"]!=original[name]["digest"]:
            raise ValueError("Published installer changed")
    cache=Path("compact-download")
    gh("release","download",tag,"--repo",repo,"--dir",cache)
    root=Path("compact-original");root.mkdir()
    # Recover originals from an already uploaded bundle on a partial retry.
    archive=zipfile.ZipFile(cache/bundle) if bundle in current else None
    try:
        if archive and sha256(cache/bundle)!=current[bundle]["digest"].removeprefix("sha256:"):
            raise ValueError("Previously uploaded archive hash differs")
        for name,item in original.items():
            target=root/name
            if name=="SHA256SUMS.txt" and archive:
                target.write_bytes(archive.read("ORIGINAL-SHA256SUMS.txt"))
            elif name in current:
                shutil.copy2(cache/name,target)
            elif archive and name not in installers:
                with archive.open(name) as src,target.open("wb") as dest:
                    shutil.copyfileobj(src,dest)
            else:
                raise ValueError("Missing original asset: "+name)
            if sha256(target)!=item["digest"].removeprefix("sha256:") or target.stat().st_size!=item["size"]:
                raise ValueError("Original asset hash/size differs: "+name)
    finally:
        if archive:archive.close()
    out=Path("compact-public")
    docs=[Path("LICENSE"),Path("THIRD_PARTY_NOTICES.md"),Path("packaging/SOURCE_AND_REPLACEMENT.md"),
          Path("packaging/build-ffmpeg.sh"),Path("packaging/opencv-image-only.json"),Path("packaging/native-sources.lock.json")]
    compact_assets(root,out,c["version"],docs)
    # Upload and confirm durable byte digests before deleting any original support.
    gh("release","upload",tag,out/bundle,out/"SHA256SUMS.txt","--repo",repo,"--clobber")
    r=release(repo,tag)
    uploaded={a["name"]:a for a in r["assets"]}
    for name in (bundle,"SHA256SUMS.txt"):
        if uploaded[name]["digest"]!="sha256:"+sha256(out/name):
            raise ValueError("Uploaded digest mismatch: "+name)
    for name in installers:
        if uploaded[name]["digest"]!=original[name]["digest"]:
            raise ValueError("Installer changed during migration")
    gh("release","edit",tag,"--repo",repo,"--notes-file","RELEASE_NOTES.md")
    for name in sorted(set(original)-installers-{"SHA256SUMS.txt"}):
        if name in uploaded:
            gh("api","--method","DELETE",f"repos/{repo}/releases/assets/{uploaded[name]['id']}")
    final=release(repo,tag)
    expected=installers|{bundle,"SHA256SUMS.txt"}
    if {a["name"] for a in final["assets"]}!=expected:
        raise ValueError("Final release must contain four uploaded assets")
    for a in final["assets"]:
        if a["digest"]!="sha256:"+sha256(out/a["name"]):
            raise ValueError("Final byte digest differs")
    Path("compact-release-report.json").write_text(json.dumps({
        "status":"PASSED","release_id":final["id"],"tag":tag,
        "support_files_preserved":len(original)-len(installers)-1,
        "assets":[{"name":a["name"],"digest":a["digest"],"size":a["size"]} for a in final["assets"]]
    },indent=2)+"\n")
    print("PASS: four public assets; all original support bytes preserved; installer hashes unchanged")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--migrate")
    parser.add_argument("--input",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--version")
    args=parser.parse_args()
    if args.migrate:migrate(args.migrate)
    else:
        docs=[Path("LICENSE"),Path("THIRD_PARTY_NOTICES.md"),Path("packaging/SOURCE_AND_REPLACEMENT.md"),
              Path("packaging/build-ffmpeg.sh"),Path("packaging/opencv-image-only.json"),Path("packaging/native-sources.lock.json")]
        compact_assets(args.input,args.output,args.version,docs)
