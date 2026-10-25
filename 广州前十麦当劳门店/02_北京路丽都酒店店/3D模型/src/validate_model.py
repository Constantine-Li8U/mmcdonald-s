# -*- coding: utf-8 -*-
"""Validation for Lido_McDonalds model files.

Run with the project venv Python (no Blender needed):
  python src/validate_model.py
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, 'models')
PREVIEWS = os.path.join(ROOT, 'previews')
report = {'project': 'McDonalds_LidoHotel_BeijingRoad_Guangzhou', 'checks': []}

def check(name, ok, detail=''):
    report['checks'].append({'check': name, 'passed': bool(ok), 'detail': str(detail)})
    return ok

FILES = ['Lido_McDonalds.blend', 'Lido_McDonalds.glb', 'Lido_McDonalds.obj',
         'Lido_McDonalds.mtl', 'Lido_McDonalds.fbx', 'model_manifest.json']
report['files'] = []
for f in FILES:
    p = os.path.join(MODELS, f)
    ok = os.path.exists(p) and os.path.getsize(p) > 0
    check('存在且非空: ' + f, ok, os.path.getsize(p) if ok else 'missing')
    if ok:
        import hashlib
        report['files'].append({'file': f, 'exists': True,
                                'bytes': os.path.getsize(p),
                                'sha256': hashlib.sha256(open(p, 'rb').read()).hexdigest()})

# BLEND header
with open(os.path.join(MODELS, 'Lido_McDonalds.blend'), 'rb') as f:
    head = f.read(12)
check('BLEND 文件头', head[:7] == b'BLENDER', head)

# GLB header + JSON chunk
glb_path = os.path.join(MODELS, 'Lido_McDonalds.glb')
with open(glb_path, 'rb') as f:
    magic, ver, length = struct.unpack('<4sII', f.read(12))
    check('GLB 文件头与长度', magic == b'glTF' and ver == 2, 'magic=%r version=%d' % (magic, ver))
    clen, ctype = struct.unpack('<II', f.read(8))
    gj = json.loads(f.read(clen).decode('utf-8'))
meshes = len(gj.get('meshes', []))
mats = len(gj.get('materials', []))
nodes = len(gj.get('nodes', []))
lights = (gj.get('extensions', {}).get('KHR_lights_punctual', {}).get('lights', []))
check('GLB 含网格与材质', meshes > 50 and mats >= 10,
      '%d meshes / %d materials / %d nodes' % (meshes, mats, nodes))
check('GLB 含门店灯光 (KHR_lights_punctual)', len(lights) >= 8,
      '%d punctual lights exported' % len(lights))
node_names = [n.get('name', '') for n in gj.get('nodes', [])]
for banned in ['Studio_shadow_ground', 'Key_large_softbox', 'Fill_cool_softbox',
               'Top_rim_softbox']:
    check('GLB 排除预览对象: ' + banned, banned not in node_names, '未导出')
for want in ['Golden_arches_M_lit_panel', 'Entrance_red_sign_box',
             'McCafe_script_on_slats', 'Lido_hotel_sign', 'White_canopy_band']:
    check('GLB 关键构件: ' + want, any(want in n for n in node_names), '存在')
# Emissive materials must be present (photo-based lit signs).
emis = [m.get('name', '') for m in gj.get('materials', [])
        if m.get('emissiveTexture') or (m.get('emissiveFactor')
           and any(c > 0 for c in m['emissiveFactor']))]
check('GLB 自发光材质数量', len(emis) >= 6, '%d emissive materials' % len(emis))

# OBJ readable + MTL
obj_path = os.path.join(MODELS, 'Lido_McDonalds.obj')
nv = nf = 0
with open(obj_path, encoding='utf-8', errors='ignore') as f:
    for line in f:
        if line.startswith('v '):
            nv += 1
        elif line.startswith('f '):
            nf += 1
check('OBJ 网格可读', nv > 20000 and nf > 15000, '%d vertices / %d faces' % (nv, nf))
with open(os.path.join(MODELS, 'Lido_McDonalds.mtl'), encoding='utf-8',
          errors='ignore') as f:
    mtl = f.read()
check('OBJ 材质库', mtl.count('newmtl') >= 10, '%d materials' % mtl.count('newmtl'))

# FBX header
with open(os.path.join(MODELS, 'Lido_McDonalds.fbx'), 'rb') as f:
    head = f.read(18)
check('FBX 二进制文件头', head.startswith(b'Kaydara FBX Binary'), head[:18])

# Previews
for f in ['Lido_01_front_day.png', 'Lido_02_oblique_day.png',
          'Lido_03_night_front.png', 'Lido_04_night_oblique.png',
          'Lido_05_night_detail.png']:
    p = os.path.join(PREVIEWS, f)
    ok = os.path.exists(p) and os.path.getsize(p) > 100000
    check('预览存在: ' + f, ok, os.path.getsize(p) if ok else 'missing')

report['all_passed'] = all(c['passed'] for c in report['checks'])
report['glb'] = {'meshes': meshes, 'materials': mats, 'nodes': nodes,
                 'lights': len(lights), 'emissive_materials': len(emis),
                 'obj_vertices': nv, 'obj_faces': nf}
out = os.path.join(MODELS, 'validation_report.json')
json.dump(report, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# Human-readable copy
lines = ['# 模型验证报告｜Lido_McDonalds', '',
         '**结论**：%s' % ('全部通过' if report['all_passed'] else '存在未通过项'), '',
         '| 检查项 | 结果 | 明细 |', '| --- | --- | --- |']
for c in report['checks']:
    lines.append('| %s | %s | %s |' %
                 (c['check'], '✅' if c['passed'] else '❌', c['detail']))
lines += ['', '网格：%d 顶点 / %d 面；GLB：%d 网格 / %d 材质 / %d 节点 / %d 盏灯 / %d 个自发光材质。'
          % (nv, nf, meshes, mats, nodes, len(lights), len(emis))]
open(os.path.join(ROOT, 'docs', '模型验证报告.md'), 'w',
     encoding='utf-8').write('\n'.join(lines))
print('VALIDATION', 'PASS' if report['all_passed'] else 'FAIL',
      '-', sum(c['passed'] for c in report['checks']), '/', len(report['checks']))
sys.exit(0 if report['all_passed'] else 1)
