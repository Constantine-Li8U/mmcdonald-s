# -*- coding: utf-8 -*-
"""Validate the Santorini Hot Spring Resort McDonald's deliverables."""
import bpy, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, 'models')
BASE = 'Santorini_Hot_Spring_Resort_McDonalds'
blend = os.path.join(MODELS, BASE + '.blend')
bpy.ops.wm.open_mainfile(filepath=blend)

required = [BASE + ext for ext in ('.blend', '.glb', '.obj', '.mtl', '.fbx')]
files = {}
for name in required:
    p = os.path.join(MODELS, name)
    files[name] = {'exists': os.path.exists(p), 'bytes': os.path.getsize(p) if os.path.exists(p) else 0}

with open(os.path.join(MODELS, BASE + '.glb'), 'rb') as f:
    glb_head = f.read(4); glb_data = f.read()
with open(os.path.join(MODELS, BASE + '.obj'), 'rb') as f:
    obj_text = f.read(4096).decode('utf-8', errors='ignore')

collection_names = sorted(c.name for c in bpy.data.collections)
required_collections = [
    '01_HOST_SHELL', '02_FACADE_STONE', '03_ARCHITECTURAL_ARCHES',
    '04_GLAZING_AND_DOORS', '05_SIGNAGE', '06_ENTRANCE_STEPS',
    '07_LIGHTING_STORE', '90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT',
    '99_REFERENCE_METADATA'
]
collection_details = {c.name: {'objects': len(c.objects), 'exported': c.name not in {
    '90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT', '99_REFERENCE_METADATA'}} for c in bpy.data.collections}

checks = {
    'all_required_files_nonempty': all(v['exists'] and v['bytes'] > 0 for v in files.values()),
    'glb_header_is_gltf': glb_head == b'glTF',
    'obj_references_mtl': ('mtllib ' + BASE + '.mtl') in obj_text,
    'preview_collection_excluded_from_glb': b'90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT' not in glb_data,
    'required_collections_present': all(n in collection_names for n in required_collections),
    'cameras_present': sum(1 for o in bpy.data.objects if o.type == 'CAMERA') >= 4,
    'store_lights_present': sum(1 for o in bpy.data.collections.get('07_LIGHTING_STORE').objects if o.type == 'LIGHT') >= 6,
    'materials_present': len(bpy.data.materials) >= 10,
}

report = {
    'project': 'Santorini_Hot_Spring_Resort_McDonalds_Guangzhou',
    'store_name': '广州圣托利温泉庄园店',
    'city': '广州市',
    'address': '广州市从化区温泉镇圣托利温泉庄园内（精确门牌待核实）',
    'accuracy_level': 'L1 photo-estimated; not surveyed; not for construction',
    'files': files,
    'collections': collection_details,
    'scene': {
        'units': bpy.context.scene.unit_settings.system,
        'cameras': [o.name for o in bpy.data.objects if o.type == 'CAMERA'],
        'lights': [o.name for o in bpy.data.objects if o.type == 'LIGHT'],
        'materials_count': len(bpy.data.materials),
    },
    'checks': checks,
    'overall': 'PASS' if all(checks.values()) else 'REVIEW_REQUIRED',
}
with open(os.path.join(MODELS, 'validation_report.json'), 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
