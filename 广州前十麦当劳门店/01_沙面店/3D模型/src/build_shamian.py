# -*- coding: utf-8 -*-
"""Parametric architectural model: McDonald's Shamian, Guangzhou.

Run with Blender 4.5 LTS:
  blender --background --python src/build_shamian.py
  blender --background --python src/build_shamian.py -- --no-render

All dimensions are photo-derived estimates, not surveyed measurements.
The script intentionally models only the building, not the street scene.
"""
import bpy
import math
import json
import os
import sys
from mathutils import Vector, Quaternion, Euler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(ROOT, 'src', 'shamian_config.json'), encoding='utf-8'))
MODELS = os.path.join(ROOT, 'models')
PREVIEWS = os.path.join(ROOT, 'previews')
os.makedirs(MODELS, exist_ok=True)
os.makedirs(PREVIEWS, exist_ok=True)

B = CONFIG['building']
A = CONFIG['arches']
S = CONFIG['storefront']
FRONT_Y = 0.0

# ---------- scene and organization ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass
for c in list(bpy.data.collections):
    if c.name != 'Collection':
        bpy.data.collections.remove(c)
def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c
COL = {
    'shell': collection('01_HOST_SHELL'),
    'stone': collection('02_FACADE_STONE'),
    'arch': collection('03_ARCHITECTURAL_ARCHES'),
    'glass': collection('04_GLAZING_AND_DOORS'),
    'sign': collection('05_SIGNAGE'),
    'steps': collection('06_ENTRANCE_STEPS'),
    'studio': collection('90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT'),
    'ref': collection('99_REFERENCE_METADATA'),
}

def move_to(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    COL[col].objects.link(obj)
    return obj

def srgb(hex_color):
    h = hex_color.lstrip('#')
    vals = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in vals)

def material(name, color, rough=0.5, metal=0.0, transmission=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    rgba = (*srgb(color), 1)
    m.diffuse_color = rgba
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = rgba
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Transmission Weight'].default_value = transmission
    if emission:
        p.inputs['Emission Color'].default_value = rgba
        p.inputs['Emission Strength'].default_value = emission
    return m

C = CONFIG['materials']
MAT = {
    'stone': material('STONE_pale_grey_limestone', C['stone'], .76),
    'trim': material('STONE_light_carved_trim', C['stone_trim'], .68),
    'mortar': material('STONE_recessed_horizontal_joints', C['mortar'], .88),
    'black': material('AWNING_matte_black', C['awning'], .58),
    'glass': material('GLASS_dark_shopfront', C['glass'], .16, .05, .55),
    'archglass': material('GLASS_dark_arch_recess', '#111817', .28, .02, .12),
    'frame': material('METAL_dark_bronze_frames', C['frame'], .32, .72),
    'gold': material('SIGN_McDonalds_golden_yellow', C['mcd_yellow'], .28, .35),
    'white': material('SIGN_warm_white_letters', C['letter_white'], .34, .05, emission=.12),
    'warm': material('INTERIOR_warm_back_panel', C['interior_warm'], .72, emission=.32),
    'light': material('INTERIOR_warm_linear_light', '#FFE0A3', .35, emission=2.5),
    'roof': material('ROOF_flat_grey_membrane', C['roof'], .88),
    'step': material('STEP_grey_stone', '#8F928E', .8),
    'ground': material('STUDIO_neutral_ground', '#E6E3DC', .85),
}

def tag(obj, part, evidence, estimated=True):
    obj['project'] = CONFIG['project']
    obj['part'] = part
    obj['visual_evidence'] = evidence
    obj['photo_estimated'] = estimated
    return obj

def bevel(obj, amount=.03, segments=2):
    mod = obj.modifiers.new('Edge_softening', 'BEVEL')
    mod.width = amount
    mod.segments = segments
    return obj

def box(name, loc, dims, mat, col, bevel_amt=0.0, evidence='photo-derived', estimated=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    if bevel_amt:
        bevel(o, bevel_amt)
    move_to(o, col)
    return tag(o, name, evidence, estimated)

def mesh_obj(name, verts, faces, mat, col, evidence='photo-derived', estimated=True):
    me = bpy.data.meshes.new(name + '_mesh')
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    COL[col].objects.link(o)
    if mat:
        me.materials.append(mat)
    return tag(o, name, evidence, estimated)

def boolean_cut(target, cutter):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new('Opening_' + cutter.name, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def rect_cut(target, name, x, z, w, h, depth=1.4):
    cutter = box(name, (x, .18, z), (w, depth, h), None, 'shell')
    boolean_cut(target, cutter)

def arch_points(cx, width, spring_z, bottom_z, samples=40):
    r = width / 2
    pts = [(cx-r, bottom_z), (cx-r, spring_z)]
    for i in range(samples + 1):
        t = math.pi - math.pi * i / samples
        pts.append((cx + r * math.cos(t), spring_z + r * math.sin(t)))
    pts.extend([(cx+r, bottom_z)])
    return pts

def prism_from_xz(name, pts, y0, y1, mat, col, evidence, estimated=True):
    n = len(pts)
    verts = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    return mesh_obj(name, verts, faces, mat, col, evidence, estimated)

def curve_path(name, pts, radius, mat, col, cyclic=False, evidence='photo-derived'):
    cu = bpy.data.curves.new(name + '_curve', 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = 2
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts)-1)
    for p, co in zip(sp.points, pts):
        p.co = (*co, 1)
    sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, cu)
    COL[col].objects.link(o)
    cu.materials.append(mat)
    return tag(o, name, evidence)

FONT = bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')
FONT_ITALIC = bpy.data.fonts.load('C:/Windows/Fonts/arialbi.ttf')
FONT_CN = bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')

def text_obj(name, body, x, y, z, size, mat, font=None, in_plane=0, extrude=.012, evidence='photo signage'):
    cu = bpy.data.curves.new(name + '_editable_text', 'FONT')
    cu.body = body
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = .003
    cu.bevel_resolution = 2
    cu.font = font or FONT
    o = bpy.data.objects.new(name, cu)
    COL['sign'].objects.link(o)
    o.location = (x, y, z)
    q = Euler((math.pi/2, 0, 0)).to_quaternion()
    if in_plane:
        q = q @ Quaternion((0, 0, 1), in_plane)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = q
    cu.materials.append(mat)
    return tag(o, name, evidence, False)

# ---------- complete host building shell ----------
w, d, h = B['width'], B['depth'], B['height']
# Separate front bands allow true openings while keeping the model easy to edit.
g = box('Facade_ground_floor_structural_wall', (0, .21, B['ground_floor_top']/2),
        (w, B['front_wall_thickness'], B['ground_floor_top']), MAT['stone'], 'stone', evidence='EXT_01;EXT_02;EXT_03;ENV_01')
a = box('Facade_arch_band_structural_wall', (0, .21, (B['ground_floor_top']+B['arch_band_top'])/2),
        (w, B['front_wall_thickness'], B['arch_band_top']-B['ground_floor_top']), MAT['stone'], 'stone', evidence='EXT_01;EXT_02;EXT_03;ENV_01')
u = box('Facade_upper_floor_structural_wall', (0, .21, (B['arch_band_top']+h)/2),
        (w, B['front_wall_thickness'], h-B['arch_band_top']), MAT['stone'], 'stone', evidence='EXT_01;EXT_02;EXT_03')

# Ground-floor openings.
openings = [
    ('Dessert_opening', S['dessert_x'], 1.93, 2.18, 2.02),
    ('Left_window_opening', S['window_left_x'], 1.97, 3.12, 2.10),
    ('M_window_opening', S['window_m_x'], 1.97, 3.12, 2.10),
    ('Entrance_opening', S['door_x'], 1.67, S['door_width'], 2.66),
    ('Right_window_opening', S['window_right_x'], 1.97, 2.25, 2.10),
]
for name, x, z, ww, hh in openings:
    rect_cut(g, name, x, z, ww, hh)
bevel(g, .025)

# Four visible semicircular arches in the wide reference photograph.
for i, cx in enumerate(A['centers_x'], 1):
    pts = arch_points(cx, A['width'], A['spring_height'], A['base_height'])
    cutter = prism_from_xz('Arch_opening_cutter_%02d' % i, pts, -.6, 1.0, None, 'arch', 'ENV_01;EXT_01')
    boolean_cut(a, cutter)
bevel(a, .025)

# Upper-floor windows: only the visible rhythm, no ornate additions.
for i, cx in enumerate([-6.5, -2.15, 2.15, 6.5], 1):
    rect_cut(u, 'Upper_window_opening_%02d' % i, cx, 8.72, 2.15, 1.86)
bevel(u, .02)

# Building side/back/floor/roof are deliberately plain inferred completion.
box('Host_left_party_wall', (-w/2+.16, d/2, h/2), (.32, d, h), MAT['stone'], 'shell', .025, 'unseen side simplified')
box('Host_right_party_wall', (w/2-.16, d/2, h/2), (.32, d, h), MAT['stone'], 'shell', .025, 'unseen side simplified')
box('Host_rear_plain_wall', (0, d-.16, h/2), (w, .32, h), MAT['stone'], 'shell', .025, 'unseen rear simplified')
for z, label in [(.12, 'Ground_floor_slab'), (4.15, 'Level_02_slab'), (7.45, 'Level_03_slab')]:
    box(label, (0, d/2, z), (w-.55, d-.35, .20), MAT['stone'], 'shell', evidence='inferred floor slab')
box('Flat_roof_inferred', (0, d/2, h+.06), (w, d, B['roof_thickness']), MAT['roof'], 'shell', .025, 'unseen roof simplified')
for x in [-w/2+.14, w/2-.14]:
    box('Roof_side_parapet', (x, d/2, h+.30), (.28, d, .48), MAT['stone'], 'shell', .02, 'unseen roof simplified')
box('Roof_rear_parapet', (0, d-.14, h+.30), (w, .28, .48), MAT['stone'], 'shell', .02, 'unseen roof simplified')

# ---------- facade mouldings and stone courses ----------
for z, hh, dep in [(4.14,.12,.20),(4.28,.10,.27),(4.40,.08,.18),(7.44,.14,.26),(7.60,.08,.17),(10.15,.16,.24)]:
    box('Continuous_cornice_z%.2f' % z, (0, -.06, z), (w+.12, dep, hh), MAT['trim'], 'stone', .018, 'EXT_01;EXT_02;EXT_03')
# Dentil-like small blocks are visible below the cornice; kept restrained.
for i in range(43):
    x = -w/2 + .24 + i * ((w-.48)/42)
    box('Cornice_small_dentil_%02d' % i, (x, -.13, 4.23), (.13,.16,.20), MAT['trim'], 'stone', .012, 'EXT_01 cornice rhythm')

# Subtract openings from course lines so joints never cross glass.
def subtract_intervals(full, cuts):
    parts = [full]
    for a0, b0 in cuts:
        out = []
        for a1, b1 in parts:
            if b0 <= a1 or a0 >= b1:
                out.append((a1,b1)); continue
            if a0 > a1: out.append((a1,a0))
            if b0 < b1: out.append((b0,b1))
        parts = out
    return parts
for zi, z in enumerate([.55,.90,1.25,1.60,1.95,2.30,2.65,3.00,3.35,3.70,4.02]):
    cuts = [(x-ww/2, x+ww/2) for _,x,zc,ww,hh in openings if zc-hh/2 < z < zc+hh/2]
    for j,(x0,x1) in enumerate(subtract_intervals((-w/2,w/2),cuts)):
        if x1-x0 > .04:
            box('Stone_horizontal_joint_%02d_%02d' % (zi,j), ((x0+x1)/2,-.012,z), (x1-x0,.016,.018), MAT['mortar'], 'stone', evidence='EXT_03;EXT_04;SIGN_03')

# Arches: recessed dark glazing and rounded light stone trim.
for i, cx in enumerate(A['centers_x'], 1):
    pts = arch_points(cx, A['width']-.10, A['spring_height'], A['base_height']+.02)
    prism_from_xz('Arch_dark_recess_%02d' % i, pts, .40, .46, MAT['archglass'], 'arch', 'EXT_01;EXT_02;EXT_03')
    path = [(cx-A['width']/2, -.075, A['base_height']),
            (cx-A['width']/2, -.075, A['spring_height'])]
    r = A['width']/2
    for k in range(49):
        t = math.pi - math.pi*k/48
        path.append((cx+r*math.cos(t),-.075,A['spring_height']+r*math.sin(t)))
    path.append((cx+A['width']/2,-.075,A['base_height']))
    curve_path('Arch_rounded_moulding_%02d' % i, path, A['trim_radius'], MAT['trim'], 'arch', evidence='EXT_01;EXT_02;EXT_03')
    box('Arch_sill_%02d' % i, (cx,-.08,A['base_height']-.03), (A['width']+.22,.24,.11), MAT['trim'], 'arch', .018, 'EXT_01')

# Upper-storey restrained cladding and glazing.
for i, cx in enumerate([-6.5,-2.15,2.15,6.5],1):
    box('Upper_window_dark_glass_%02d'%i,(cx,.38,8.72),(2.06,.06,1.77),MAT['glass'],'glass',evidence='EXT_01;EXT_03')
    for dx in [-1.09,1.09]:
        box('Upper_window_frame_%02d'%i,(cx+dx,.25,8.72),(.07,.12,1.92),MAT['frame'],'glass',evidence='EXT_01')
    box('Upper_window_center_mullion_%02d'%i,(cx,.23,8.72),(.06,.12,1.82),MAT['frame'],'glass',evidence='EXT_01')
for x in [-8.65,-4.32,0,4.32,8.65]:
    box('Upper_vertical_cladding_joint', (x,-.012,8.88), (.045,.022,2.45), MAT['mortar'], 'stone', evidence='EXT_01;EXT_03')

# ---------- storefront glazing, frames and awnings ----------
def storefront_window(label, x, width, awning=True):
    zc = 1.97
    hh = 2.10
    box(label+'_dark_glazing',(x,.40,zc),(width-.10,.06,hh-.08),MAT['glass'],'glass',evidence='EXT_01;EXT_03;CNT_01')
    for dx in [-width/2+.05,width/2-.05]:
        box(label+'_side_frame',(x+dx,.19,zc),(.09,.16,hh),MAT['frame'],'glass',.01,'EXT_03')
    for z in [zc-hh/2+.04,zc+hh/2-.04]:
        box(label+'_horizontal_frame',(x,.19,z),(width,.16,.08),MAT['frame'],'glass',.01,'EXT_03')
    box(label+'_stone_sill',(x,-.10,.88),(width+.16,.34,.13),MAT['trim'],'stone',.02,'EXT_01;EXT_03')
    for dx in [-width*.34,width*.34]:
        box(label+'_sill_corbel',(x+dx,-.03,.74),(.25,.20,.19),MAT['trim'],'stone',.015,'EXT_03;EXT_04')
    # Warm interior backing is intentionally abstract, without people/furniture.
    box(label+'_warm_interior',(x,1.12,1.95),(width-.20,.06,1.88),MAT['warm'],'glass',evidence='CNT_01 warm interior simplified')
    if awning:
        box(label+'_black_awning',(x,-.25,3.12),(width+.24,.66,.34),MAT['black'],'sign',.035,'EXT_01;EXT_03')
        text_obj(label+'_awning_McDonalds',"McDonald's",x,-.593,3.13,.235,MAT['white'],evidence='EXT_01;EXT_03')

storefront_window('Dessert_station',S['dessert_x'],2.18,False)
storefront_window('Left_display_window',S['window_left_x'],3.12,True)
storefront_window('Golden_M_display_window',S['window_m_x'],3.12,True)
storefront_window('Right_display_window',S['window_right_x'],2.25,True)

text_obj('Dessert_station_Chinese_sign','甜品站',S['dessert_x'],-.10,3.42,.38,MAT['white'],font=FONT_CN,extrude=.018,evidence='EXT_02;EXT_05;CNT_02')
text_obj('Vertical_McCafe_sign','McCafé',-1.86,-.10,2.02,.39,MAT['white'],font=FONT_ITALIC,in_plane=math.pi/2,extrude=.014,evidence='EXT_04;ENV_01')
text_obj('Upper_McDonalds_channel_letters',"McDonald's",-3.48,-.12,7.02,1.05,MAT['white'],extrude=.09,evidence='EXT_02;EXT_05;ENV_01')

# Entrance with two glazed leaves, dark bronze framing and simple pull handles.
dx = S['door_x']
box('Entrance_dark_glass',(dx,.40,1.67),(S['door_width']-.10,.07,2.58),MAT['glass'],'glass',evidence='EXT_01;EXT_03;SIGN_01')
for sx in [-1,1]:
    box('Entrance_outer_jamb',(dx+sx*(S['door_width']/2-.04),.13,1.67),(.09,.20,2.70),MAT['frame'],'glass',.01,'EXT_03')
box('Entrance_center_mullion',(dx,.12,1.64),(.07,.18,2.62),MAT['frame'],'glass',.01,'EXT_03')
for z in [.36,3.0]:
    box('Entrance_head_threshold',(dx,.12,z),(S['door_width'],.20,.09),MAT['frame'],'glass',.01,'EXT_03')
for sx in [-1,1]:
    x = dx+sx*.17
    curve_path('Entrance_vertical_pull_handle',[(x,-.04,1.23),(x,-.04,1.93)],.025,MAT['trim'],'glass',evidence='EXT_03;SIGN_01')
    for z in [1.28,1.88]:
        curve_path('Entrance_handle_standoff',[(x,-.04,z),(x,.08,z)],.018,MAT['trim'],'glass',evidence='EXT_03')
text_obj('Entrance_McCafe_wordmark','McCafé',dx+.54,-.03,2.69,.22,MAT['white'],font=FONT_ITALIC,evidence='EXT_01;SIGN_01')

# Three entry steps from the photographs, no sidewalk/street geometry.
for i in range(3):
    # Largest and lowest slab at the front; progressively smaller slabs rise toward the door.
    box('Entrance_step_%02d'%(i+1),(dx,-.55-(2-i)*.29,.06+i*.06),
        (2.48+(2-i)*.16,.72+(2-i)*.52,.12+i*.12),MAT['step'],'steps',.025,'EXT_01;EXT_03')

# ---------- giant freestanding golden M ----------
def cubic(p0,p1,p2,p3,n=18):
    out=[]
    for i in range(n+1):
        t=i/n; u=1-t
        out.append((u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0],
                    u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]))
    return out
# One concave outline, not two overlapping toruses. Dimensions normalized then scaled.
left_outer = cubic((-1.45,.80),(-1.45,2.02),(-1.17,2.91),(-.73,3.00),24)
right_outer = [(-x,z) for x,z in reversed(left_outer)]
left_inner = cubic((-1.00,.75),(-1.00,1.77),(-.98,2.29),(-.72,2.40),22)
right_inner = [(-x,z) for x,z in reversed(left_inner)]
outline = [(-1.45,0.0)] + left_outer + [(-.34,1.93),(0,1.28),(.34,1.93),(.73,3.00)] + right_outer + [(1.45,0.0),(1.00,0.0)] + list(reversed(right_inner)) + [(.30,1.60),(0,1.02),(-.30,1.60)] + left_inner + [(-1.00,0.0)]
# Remove consecutive duplicates.
clean=[]
for p in outline:
    if not clean or (abs(p[0]-clean[-1][0])+abs(p[1]-clean[-1][1])>.0001): clean.append(p)
outline=clean
sx = S['m_width']/2.90
sz = S['m_height']/3.00
pts=[(S['window_m_x']+x*sx,S['m_base']+z*sz) for x,z in outline]
M = prism_from_xz('Golden_arches_M_freestanding',pts,-.57,-.31,MAT['gold'],'sign','EXT_01;EXT_03;SIGN_01;SIGN_02',False)
bevel(M,.025,3)
M['landmark'] = '广州最大落地金拱门 M 招牌（门店资料口径）'

# Subtle vertical warm tubes seen through the windows; no interior furniture.
for x in [S['window_left_x']-.72,S['window_left_x']-.20,S['window_m_x']+.86]:
    curve_path('Interior_warm_light_tube',[(x,.72,1.67),(x,.72,2.45)],.025,MAT['light'],'glass',evidence='CNT_01;EXT_04')

# ---------- reference metadata, lighting and cameras ----------
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.length_unit='METERS'
scene['model_scope']='Only McDonalds Shamian building; no surrounding scene'
scene['dimensional_accuracy']='Photo-estimated proportions; not surveyed'
scene['reference_photos']='01_沙面_EXT_01..05;SIGN_01..04;CNT_01..02;ENV_01'
scene['source_script']='src/build_shamian.py'
scene['config']='src/shamian_config.json'

# Camera-facing preview studio is excluded from every model export.
box('Studio_shadow_ground',(0,1,-.18),(200,200,.10),MAT['ground'],'studio',evidence='preview only')
world=bpy.data.worlds.new('Neutral_architectural_world')
scene.world=world
world.use_nodes=True
world_bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
world_bg.inputs[0].default_value=(.72,.77,.82,1)
world_bg.inputs[1].default_value=.45

def area(name,loc,power,size,color,target):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size; data.color=color
    o=bpy.data.objects.new(name,data); COL['studio'].objects.link(o); o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
area('Key_large_softbox',(-8,-12,18),2300,9,(1.0,.90,.78),(0,0,4))
area('Fill_cool_softbox',(10,-7,11),1700,8,(.78,.88,1.0),(0,1,4))
area('Roof_rim_softbox',(1,8,17),2600,7,(1.0,.96,.88),(0,2,5))

def camera(name,loc,target,ortho):
    data=bpy.data.cameras.new(name); data.type='ORTHO'; data.ortho_scale=ortho; data.lens=48
    o=bpy.data.objects.new(name,data); COL['studio'].objects.link(o); o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
CAMS={
    '01_front':camera('CAM_01_front_elevation',(0,-31,7.4),(0,1.3,5.0),21.8),
    '02_oblique':camera('CAM_02_three_quarter',(18,-28,16),(0,1.4,4.8),24.5),
    '03_detail':camera('CAM_03_storefront_detail',(8,-21,7.0),(0,.0,2.45),14.0),
}
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.cycles.max_bounces=8
scene.render.resolution_x=1500
scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.color_mode='RGBA'

# Set the .blend opening view to the main camera and material mode.
scene.camera=CAMS['02_oblique']
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            ar.spaces.active.region_3d.view_perspective='CAMERA'
            ar.spaces.active.shading.type='MATERIAL'

# Embed a concise in-file guide.
t=bpy.data.texts.new('READ_ME_模型说明')
t.write('麦当劳沙面店｜参数化建筑模型\n\n单位：米。尺寸均为照片推定，非实测。\n'
        '01-06 集合为建筑本体；90 为预览灯光/地面；导出文件不含 90。\n'
        '文字在 .blend 中保持可编辑；脚本与 shamian_config.json 可复建。\n'
        '临街立面依据 EXT_01..05 / SIGN_01..04 / CNT_01..02 / ENV_01。\n'
        '背、侧、屋顶为克制补全；无人物、车辆、道路、植物及装饰图标。\n')
bpy.ops.file.pack_all()
blend_path=os.path.join(MODELS,'Shamian_McDonalds.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

# Convert text only in the export session; the saved .blend retains editable text.
bpy.ops.object.select_all(action='DESELECT')
for o in list(COL['sign'].objects):
    if o.type in {'FONT','CURVE'}:
        o.select_set(True)
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.convert(target='MESH')
        o.select_set(False)
model_objects=[]
for key in ['shell','stone','arch','glass','sign','steps']:
    model_objects.extend([o for o in COL[key].objects if o.type in {'MESH','CURVE'}])
bpy.ops.object.select_all(action='DESELECT')
for o in model_objects:
    o.select_set(True)
bpy.context.view_layer.objects.active=model_objects[0]

bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS,'Shamian_McDonalds.glb'),
    export_format='GLB',use_selection=True,export_apply=True,export_yup=True,
    export_materials='EXPORT',export_extras=True)
bpy.ops.wm.obj_export(filepath=os.path.join(MODELS,'Shamian_McDonalds.obj'),
    export_selected_objects=True,apply_modifiers=True,export_materials=True,path_mode='COPY')
try:
    bpy.ops.export_scene.fbx(filepath=os.path.join(MODELS,'Shamian_McDonalds.fbx'),
        use_selection=True,use_mesh_modifiers=True,add_leaf_bones=False)
except Exception as e:
    print('FBX export warning:',e)

if '--no-render' not in sys.argv:
    for key,cam in CAMS.items():
        scene.camera=cam
        scene.render.filepath=os.path.join(PREVIEWS,'Shamian_'+key+'.png')
        bpy.ops.render.render(write_still=True)

# Export metrics and scene inventory.
mesh_stats={'vertices':0,'polygons':0,'objects':len(model_objects),'collections':[]}
for o in model_objects:
    if o.type=='MESH':
        mesh_stats['vertices']+=len(o.data.vertices)
        mesh_stats['polygons']+=len(o.data.polygons)
for key in ['shell','stone','arch','glass','sign','steps']:
    mesh_stats['collections'].append({'name':COL[key].name,'objects':len(COL[key].objects)})
mesh_stats['dimensions_m']={'width':w,'depth':d,'height':h+.54}
mesh_stats['scale_note']=CONFIG['scale_basis']
mesh_stats['source_photos']=scene['reference_photos']
mesh_stats['exports']=['Shamian_McDonalds.blend','Shamian_McDonalds.glb','Shamian_McDonalds.obj','Shamian_McDonalds.fbx']
json.dump(mesh_stats,open(os.path.join(MODELS,'model_manifest.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=2)
print('BUILD_COMPLETE',json.dumps(mesh_stats,ensure_ascii=False))
