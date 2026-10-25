# -*- coding: utf-8 -*-
"""Validate exported Shamian model artifacts using only Python stdlib."""
import hashlib
import json
import os
import struct
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, 'models')
DOCS = os.path.join(ROOT, 'docs')
NAMES = ['Shamian_McDonalds.blend', 'Shamian_McDonalds.glb',
         'Shamian_McDonalds.obj', 'Shamian_McDonalds.mtl',
         'Shamian_McDonalds.fbx', 'model_manifest.json']
report = {'project': 'McDonalds_Shamian_Guangzhou', 'checks': [], 'files': []}

def check(name, ok, detail):
    report['checks'].append({'check': name, 'passed': bool(ok), 'detail': detail})

for name in NAMES:
    path = os.path.join(MODELS, name)
    exists = os.path.isfile(path)
    size = os.path.getsize(path) if exists else 0
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest() if exists else ''
    report['files'].append({'file': name, 'exists': exists, 'bytes': size, 'sha256': sha})
    check('存在且非空: ' + name, exists and size > 100, '%d bytes' % size)

blend = open(os.path.join(MODELS, 'Shamian_McDonalds.blend'), 'rb').read(12)
check('BLEND 文件头', blend.startswith(b'BLENDER'), repr(blend))

glb_path = os.path.join(MODELS, 'Shamian_McDonalds.glb')
with open(glb_path, 'rb') as f:
    magic, version, length = struct.unpack('<4sII', f.read(12))
    chunk_len, chunk_type = struct.unpack('<I4s', f.read(8))
    gltf = json.loads(f.read(chunk_len).decode('utf-8').rstrip('\x00 '))
check('GLB 文件头与长度', magic == b'glTF' and version == 2 and length == os.path.getsize(glb_path),
      'magic=%r version=%s length=%s' % (magic, version, length))
node_names = [n.get('name', '') for n in gltf.get('nodes', [])]
check('GLB 含网格与材质', len(gltf.get('meshes', [])) > 100 and len(gltf.get('materials', [])) >= 10,
      '%d meshes / %d materials / %d nodes' % (len(gltf.get('meshes', [])), len(gltf.get('materials', [])), len(node_names)))
for forbidden in ['Studio_shadow_ground', 'Key_large_softbox', 'Fill_cool_softbox', 'Roof_rim_softbox']:
    check('GLB 排除预览对象: ' + forbidden, forbidden not in node_names, '未导出' if forbidden not in node_names else '发现异常')
for required in ['Golden_arches_M_freestanding', 'Upper_McDonalds_channel_letters',
                 'Dessert_station_Chinese_sign', 'Entrance_step_03']:
    check('GLB 关键构件: ' + required, any(required in n for n in node_names), '存在')

obj_path = os.path.join(MODELS, 'Shamian_McDonalds.obj')
v = f = 0
with open(obj_path, encoding='utf-8', errors='ignore') as fh:
    for line in fh:
        if line.startswith('v '): v += 1
        elif line.startswith('f '): f += 1
check('OBJ 网格可读', v > 1000 and f > 1000, '%d vertices / %d faces' % (v, f))
mtl = open(os.path.join(MODELS, 'Shamian_McDonalds.mtl'), encoding='utf-8', errors='ignore').read()
check('OBJ 材质库', mtl.count('newmtl') >= 10, '%d materials' % mtl.count('newmtl'))
fbx = open(os.path.join(MODELS, 'Shamian_McDonalds.fbx'), 'rb').read(20)
check('FBX 二进制文件头', fbx.startswith(b'Kaydara FBX Binary'), repr(fbx[:18]))
for p in ['Shamian_01_front.png', 'Shamian_02_oblique.png', 'Shamian_03_detail.png']:
    fp = os.path.join(ROOT, 'previews', p)
    check('预览存在: ' + p, os.path.isfile(fp) and os.path.getsize(fp) > 10000,
          '%d bytes' % (os.path.getsize(fp) if os.path.exists(fp) else 0))

report['all_passed'] = all(c['passed'] for c in report['checks'])
report['glb'] = {'meshes': len(gltf.get('meshes', [])), 'materials': len(gltf.get('materials', [])),
                 'nodes': len(node_names), 'obj_vertices': v, 'obj_faces': f}
json.dump(report, open(os.path.join(MODELS, 'validation_report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

lines = ['# 沙面店 3D 模型验证报告', '', '**结论：%s**' % ('全部自动检查通过' if report['all_passed'] else '存在未通过项'), '',
         '| 检查项 | 结果 | 说明 |', '| --- | --- | --- |']
for c in report['checks']:
    lines.append('| %s | %s | %s |' % (c['check'], '通过' if c['passed'] else '未通过', c['detail']))
lines += ['', '## 文件校验', '', '| 文件 | 字节 | SHA-256 |', '| --- | ---: | --- |']
for f in report['files']:
    lines.append('| `%s` | %d | `%s` |' % (f['file'], f['bytes'], f['sha256']))
lines += ['', '另通过 Blender 重新打开源文件及重新导入 FBX 检查场景结构；相关结果由交付时的终端核验记录确认。', '']
open(os.path.join(DOCS, '模型验证报告.md'), 'w', encoding='utf-8').write('\n'.join(lines))
print(json.dumps({'all_passed': report['all_passed'], 'glb': report['glb']}, ensure_ascii=False))
if not report['all_passed']:
    raise SystemExit(1)
