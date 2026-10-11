"""Bind reviewed native installer evidence to actual installed bundle bytes."""
import argparse,json,os,runpy,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def openssl_license_evidence(root):
    # Select an exact component path and compare to reviewed repository originals.
    # A Python/NumPy Apache document cannot stand in for OpenSSL.
    import hashlib
    root=Path(root).absolute()
    result={}
    # Audit receives the outer .app/install directory. Datas use these exact
    # PyInstaller layouts; don't select arbitrary matching files via rglob.
    candidates=[root/path for path in ('licenses','_internal/licenses','Contents/Resources/licenses')
                if (root/path).exists() or (root/path).is_symlink()]
    if len(candidates)!=1:
        raise ValueError('OpenSSL license directory missing or ambiguous')
    licenses=candidates[0]
    if not licenses.is_dir() or any(p.is_symlink() for p in (licenses,*licenses.parents) if p==root or root in p.parents):
        raise ValueError('OpenSSL license directory unsafe')
    for name,key in (('OpenSSL-LICENSE.txt','installed_license'),('RUNTIME-NOTICES.md','installed_notices')):
        installed=licenses/name
        original=ROOT/'packaging/third-party'/name
        if (installed.is_symlink() or not installed.is_file() or
                installed.read_bytes()!=original.read_bytes()):
            raise ValueError('OpenSSL dedicated license/notice missing or changed: '+name)
        result[key]=installed.relative_to(root).as_posix()
        result[key+'_sha256']=hashlib.sha256(installed.read_bytes()).hexdigest()
    result['license_basis']='Repository original OpenSSL-LICENSE.txt and RUNTIME-NOTICES.md; OpenSSL 3.x runtime version verified separately'
    return result

def review(root,inputs,candidate,config,platform,output):
    assert config['native_inventory_reviewed'] is True
    audit_module=runpy.run_path(str(ROOT/'packaging/audit_release.py'))
    digest=audit_module['sha256']
    files=[p for p in root.rglob('*') if p.is_file()]
    def one(name):
        matches=[p for p in files if p.name==name and not p.is_symlink()]
        if not matches:raise ValueError('Installed material missing: '+name)
        return matches[0]
    build=json.loads(one('build-manifest.json').read_text())
    assert build['version']==config['version']
    assert build['provenance']['GITHUB_SHA']==config['candidate_commit']
    assert str(build['provenance']['GITHUB_RUN_ID'])==str(config['candidate_run_id'])
    assert digest(one('build-manifest.json'))==digest(candidate/'build/build-manifest.json')
    inventory=json.loads((candidate/'build/candidate-inventory.json').read_text())
    assert inventory['build_manifest_sha256']==digest(one('build-manifest.json'))
    sources=json.loads((ROOT/'packaging/native-sources.lock.json').read_text())
    for item in sources.values():
        assert digest(inputs/'sources'/item['url'].rsplit('/',1)[-1])==item['sha256']
    opencv=json.loads((candidate/'build/opencv-build.json').read_text())
    assert opencv['image_only_verified']
    assert digest(inputs/'sources'/opencv['source_patch'])==opencv['source_patch_sha256']
    runpy.run_path(str(ROOT/'packaging/native_codec_policy.py'))['verify_no_extra_codecs'](root)
    for name in ('installed-smoke.json','installer-smoke.json','qt-replacement-smoke.json'):
        r=json.loads((candidate/'build'/name).read_text())
        assert r['status']=='success' and r['frozen'] and r['bundled_tools_checked']
        assert r['version']==config['version'] and r['pdf_only_checked'] and r['output_lock_cleanup_checked']
    replacement=json.loads((candidate/'build/qt-replacement.json').read_text())
    modified=json.loads((candidate/'build/qt-replacement-smoke.json').read_text())
    assert modified['qt_runtime_version']==replacement['expected_runtime_version']=='6.12.9'
    core=one('Qt6Core.dll' if sys.platform=='win32' else 'QtCore')
    assert digest(core)==replacement['original_sha256']!=replacement['modified_sha256']
    native=lambda:sorted({p.relative_to(root).as_posix() for p in files if not p.is_symlink() and (p.suffix.lower() in ('.dll','.dylib','.pyd','.so') or '.framework/Versions/' in p.as_posix())})
    assert digest(candidate/'build/native-library-files.json')==config['reviewed_native_inventory_sha256'][platform]
    expected=json.loads((candidate/'build/native-library-files.json').read_text())
    assert native()==expected,'Installed native library inventory differs'
    modules=sorted({p.name for p in files if p.name.startswith('Qt6') and p.suffix=='.dll'}|{p.name for p in files if p.parent.name=='A' and p.name.startswith('Qt')})
    assert modules
    data=json.loads((inputs/'binary-manifest.json').read_text())
    for name in ('ffmpeg','ffprobe'):
        tool=one(name+('.exe' if sys.platform=='win32' else ''))
        assert digest(tool)==inventory['tools'][name]['bundle_sha256']
        data[name]['bundle_sha256']=digest(tool)
    for name in ('ffmpeg','qt'):
        item=sources[name]
        data.setdefault(name,{}).update(version=item['version'],corresponding_source_url=item['url'],source_sha256=item['sha256'],source_archive_local=str((inputs/'sources'/item['url'].rsplit('/',1)[-1]).resolve()))
    data['qt'].update(modules=modules,replacement_verified=True,replacement_evidence=replacement)
    assert one('LICENSE').read_text().startswith('MIT License')
    one('THIRD_PARTY_NOTICES.md');one('SOURCE_AND_REPLACEMENT.md');one('SBOM.json')
    assert any('licenses' in p.relative_to(root).parts and p.stat().st_size for p in files)
    assert not any(any(k in p.name.lower() for k in ('pymupdf','fitz','pytest','test_lecture')) for p in files)
    data['bundle']={**inventory,'third_party_notices_included':True,'license_copies_included':True,'sbom_included':True,'pymupdf_absent':True,'clean_machine_smoke_verified':True,'native_installer_verified':True,'signed_or_notarization_state_recorded':True,'signing_state':'macOS ad-hoc, not notarized' if sys.platform=='darwin' else 'Windows unsigned'}
    crypto=next((p for p in files if not p.is_symlink() and 'libcrypto' in p.name.lower() and p.suffix.lower() in ('.dll','.dylib')),None)
    if crypto:
        import ctypes
        library=ctypes.CDLL(str(crypto.resolve()))
        library.OpenSSL_version.argtypes=[ctypes.c_int];library.OpenSSL_version.restype=ctypes.c_char_p
        ssl_version=library.OpenSSL_version(0).decode()
        assert ssl_version.startswith('OpenSSL 3.'),ssl_version
        data['openssl']={'version':ssl_version,'path':crypto.relative_to(root).as_posix(),'sha256':digest(crypto),'license':'Apache-2.0',**openssl_license_evidence(root)}
        print('OPENSSL_NATIVE_RUNTIME',json.dumps(data['openssl']))
    data['status']='APPROVED'
    data['review_scope']='Exact candidate and installed native inventory; LGPL replacement smoke; corresponding sources and original notices. Not a legal compliance certificate.'
    output.mkdir(parents=True,exist_ok=True)
    manifest=output/'reviewed-manifest.json';manifest.write_text(json.dumps(data,indent=2)+'\n')
    errors=audit_module['audit'](root,one('ffmpeg'+('.exe' if sys.platform=='win32' else '')),manifest)
    installer=next((candidate/'dist').glob('*.dmg' if sys.platform=='darwin' else '*Setup-Windows-x64.exe'))
    report={'status':'BLOCKED' if errors else 'PASSED','errors':errors,'version':config['version'],'commit':config['candidate_commit'],'run_id':str(config['candidate_run_id']),'platform':platform,'installer_sha256':digest(installer),'manifest_sha256':digest(manifest)}
    if errors:
        data['status']='NOT_APPROVED'
        manifest.write_text(json.dumps(data,indent=2)+'\n')
        report['manifest_sha256']=digest(manifest)
    (output/'audit-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REVIEWED_NATIVE_MODULES',json.dumps(modules));print('CANDIDATE_AUDIT',json.dumps(report))
    if errors:raise ValueError(errors)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','inputs','candidate','config','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--platform',required=True);a=p.parse_args()
    review(a.root,a.inputs,a.candidate,json.loads(a.config.read_text()),a.platform,a.output)
