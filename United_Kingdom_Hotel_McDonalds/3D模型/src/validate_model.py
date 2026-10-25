# -*- coding: utf-8 -*-
"""Structural validation for the exported United Kingdom Hotel model."""
import bpy, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, 'models')
blend = os.path.join(MODELS, 'United_Kingdom_Hotel_McDonalds.blend')
bpy.ops.wm.open_mainfile(filepath=blend)

required = [
    'United_Kingdom_Hotel_McDonalds.blend',
    'United_Kingdom_Hotel_McDonalds.glb',
    'United_Kingdom_Hotel_McDonalds.obj',
    'United_Kingdom_Hotel_McDonalds.mtl',
    'United_Kingdom_Hotel_McDonalds.fbx',
]
files = {}
for name in required:
    p = os.path.join(MODELS, name)
    files[name] = {'exists': os.path.exists(p), 'bytes': os.path.getsize(p) if os.path.exists(p) else 0}

glb_path = os.path.join(MODELS, 'United_Kingdom_Hotel_McDonalds.glb')
obj_path = os.path.join(MODELS, 'United_Kingdom_Hotel_McDonalds.obj')
with open(glb_path, 'rb') as f:
    glb_head = f.read(4)
    glb_data = f.read()
with open(obj_path, 'rb') as f:
    obj_text = f.read(4096).decode('utf-8', errors='ignore')

collection_names = sorted(c.name for c in bpy.data.collections)
collection_details = {}
for c in bpy.data.collections:
    exported = c.name not in {'90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT', '99_REFERENCE_METADATA'}
    collection_details[c.name] = {'objects': len(c.objects), 'exported': exported}

checks = {
    'all_required_files_nonempty': all(v['exists'] and v['bytes'] > 0 for v in files.values()),
    'glb_header_is_gltf': glb_head == b'glTF',
    'obj_references_mtl': 'mtllib United_Kingdom_Hotel_McDonalds.mtl' in obj_text,
    'preview_collection_excluded_from_glb': b'90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT' not in glb_data,
    'required_collections_present': all(name in collection_names for name in [
        '01_HOST_SHELL', '02_FACADE_STONE', '03_ARCHITECTURAL_ARCHES',
        '04_GLAZING_AND_DOORS', '05_SIGNAGE', '06_ENTRANCE_STEPS',
        '07_LIGHTING_STORE', '90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT',
        '99_REFERENCE_METADATA']),
    'cameras_present': sum(1 for o in bpy.data.objects if o.type == 'CAMERA') >= 4,
    'store_lights_present': sum(1 for o in bpy.data.objects if o.type == 'LIGHT') >= 6,
    'materials_present': len(bpy.data.materials) >= 10,
}

report = {
    'project': 'United_Kingdom_Hotel_McDonalds_Melbourne',
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
out = os.path.join(MODELS, 'validation_report.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
