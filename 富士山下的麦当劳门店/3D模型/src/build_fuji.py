# -*- coding: utf-8 -*-
"""Parametric dusk-scene model: McDonald's on Route 139, Fujiyoshida, with
Mt. Fuji as a mandatory, non-removable backdrop.

Run with Blender 4.5:
  blender --background --python src/build_fuji.py
  blender --background --python src/build_fuji.py -- --no-render

Reference: the user-supplied dusk photo (REF_USER). The composition, colour
and detail must follow that photo. Every dimension is photo-derived estimate,
not surveyed. Mt. Fuji, the mist band, far hills, conifers and the wet
asphalt foreground are explicit user requirements (scene-type deliverable),
so they live in collection 08_ENVIRONMENT_FUJI and ARE exported, unlike the
series default of building the bare building only.

The reference photo is an artistic composition: the apparent angular size of
Fuji relative to the storefront cannot be reproduced by one physical camera.
We therefore match the photo composition visually in the hero render and
document the compromise (see docs/富士山店_照片分析与建模记录.md).
"""
import bpy
import math
import json
import os
import sys
from mathutils import Vector, Euler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(ROOT, 'src', 'fuji_config.json'), encoding='utf-8'))
MODELS = os.path.join(ROOT, 'models')
PREVIEWS = os.path.join(ROOT, 'previews')
os.makedirs(MODELS, exist_ok=True)
os.makedirs(PREVIEWS, exist_ok=True)

B = CONFIG['building']
RS = CONFIG['roof_sign_band']
FA = CONFIG['facade']
PS = CONFIG['pole_sign']
FJ = CONFIG['fuji']
LC = CONFIG['lighting']
C = CONFIG['materials']

# ---------- 昼夜变体：WEB 端需要在白天显示「关灯」状态、夜间显示「亮灯」状态 ----------
# 同一份几何，两套材质（夜色石材 vs 日间石材）+ 两套灯光（门店暖光 vs 日光）。
ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
THEME = 'day' if ('--theme' in ARGV and ARGV[ARGV.index('--theme') + 1:ARGV.index('--theme') + 2] == ['day']) else 'night'
if THEME == 'day':
    C = {**C, **CONFIG['materials_day']}
GLB_NAME = 'Fuji_McDonalds_day.glb' if THEME == 'day' else 'Fuji_McDonalds.glb'
BLEND_NAME = 'Fuji_McDonalds_day.blend' if THEME == 'day' else 'Fuji_McDonalds.blend'

# ---------- scene reset and collections ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection':
        bpy.data.collections.remove(c)

def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c

COL = {
    'shell': collection('01_HOST_SHELL'),
    'facade': collection('02_FACADE_CLADDING'),
    'glass': collection('04_GLAZING_AND_DOORS'),
    'sign': collection('05_SIGNAGE'),
    'env': collection('08_ENVIRONMENT_FUJI'),
    'light': collection('07_LIGHTING_STORE'),
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

def material(name, color, rough=0.5, metal=0.0, emission=0.0, emission_color=None,
             alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    rgba = (*srgb(color), 1)
    m.diffuse_color = rgba
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = rgba
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if THEME == 'day':
        emission = 0.0   # 白天：招牌/室内发光全部关闭
    if emission:
        p.inputs['Emission Color'].default_value = (*srgb(emission_color or color), 1)
        p.inputs['Emission Strength'].default_value = emission
    if alpha < 1.0:
        p.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'
    return m

MAT = {
    'roof': material('ROOF_black_flat_membrane', C['roof_black'], .82),
    'band': material('BAND_black_fascia', C['band_black'], .78),
    'band_lit': material('BAND_black_sign_backing_night', C['band_black'], .7,
                         emission=.25, emission_color='#0D1016'),
    'red': material('SIGN_red_panel', C['red'], .45),
    'red_lit': material('SIGN_red_panel_night', C['red'], .42,
                        emission=LC['red_glow']),
    'gold': material('SIGN_McDonalds_golden_yellow', C['mcd_yellow'], .3, .3),
    'gold_lit': material('SIGN_golden_M_lit_night', C['mcd_yellow'], .28, .12,
                         emission=LC['m_glow']),
    'white_lit': material('SIGN_wordmark_lit_night', C['letter_white'], .34,
                          emission=2.2),
    'white_flat': material('SIGN_open_board_letters', C['letter_white'], .4),
    'open_lit': material('SIGN_open24_board_night', '#0C0E12', .7,
                         emission=.32, emission_color='#1A1D24'),
    'glass': material('GLASS_dusk_shopfront', C['glass_dark'], .12, .04, alpha=.55),
    'frame': material('METAL_dark_mullions', C['frame_dark'], .36, .7),
    'interior_glow': material('INTERIOR_warm_backlight_panel', C['interior_warm'],
                              .6, emission=3.0,
                              emission_color=LC['interior_warm_light']),
    'interior_deep': material('INTERIOR_furniture_silhouette', C['interior_deep'], .8),
    'pole': material('METAL_pole_sign_grey', C['pole_grey'], .5, .25),
    'tree': material('FOLIAGE_conifer_silhouette', C['tree_green'], .9),
    'fuji_snow': material('TERRAIN_fuji_snowcap_dusk', C['fuji_snow'], .68,
                          emission=.1, emission_color='#DFE9F5'),
    'fuji_body': material('TERRAIN_fuji_slope_blue', C['fuji_body'], .9,
                          emission=.06, emission_color='#4E608A'),
    'fuji_foot': material('TERRAIN_fuji_foothill_dark', C['fuji_foot'], .95,
                          emission=.02, emission_color='#33405E'),
    'mist': material('ATMOS_mist_layer_soft', C['mist'], .9, alpha=.06,
                     emission=.04, emission_color='#8AA0C4'),
    'mist_dense': material('ATMOS_mist_layer_dense', C['mist'], .9, alpha=.1,
                           emission=.06, emission_color='#93A9CC'),
    'far_hill': material('TERRAIN_far_hills_silhouette', C['far_hill'], .95,
                         emission=.05, emission_color='#3A4C74'),
    'ground': material('GROUND_wet_asphalt_dusk', C['ground_wet'], .22, .08),
    'studio_ground': material('STUDIO_neutral_ground', '#20242C', .85),
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

def box(name, loc, dims, mat, col, bevel_amt=0.0, evidence='REF_USER photo-derived',
        estimated=True):
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

def cyl(name, loc, radius, depth, mat, col, rot=(0, 0, 0), vertices=24,
        evidence='REF_USER photo-derived', estimated=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                        location=loc, rotation=rot,
                                        vertices=vertices)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    move_to(o, col)
    return tag(o, name, evidence, estimated)

def cone(name, loc, r_base, r_top, depth, mat, col, vertices=96,
         evidence='REF_USER photo-derived', estimated=True):
    bpy.ops.mesh.primitive_cone_add(radius1=r_base, radius2=r_top, depth=depth,
                                    location=loc, vertices=vertices)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    move_to(o, col)
    return tag(o, name, evidence, estimated)

def uv_sphere(name, loc, radius, scale, mat, col, evidence, estimated=True):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc,
                                         segments=48, ring_count=24)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    move_to(o, col)
    return tag(o, name, evidence, estimated)

def text_obj(name, body, x, y, z, size, mat, font=None, extrude=.02,
             evidence='REF_USER signage'):
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
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Euler((math.pi / 2, 0, 0)).to_quaternion()
    cu.materials.append(mat)
    return tag(o, name, evidence, False)

FONT = bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')

# ---------- golden arches M outline (shared series asset) ----------
def cubic(p0, p1, p2, p3, n=18):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append((u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                    u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]))
    return out

def m_outline(cx, base_z, width, height):
    left_outer = cubic((-1.45, .80), (-1.45, 2.02), (-1.17, 2.91), (-.73, 3.00), 24)
    right_outer = [(-x, z) for x, z in reversed(left_outer)]
    left_inner = cubic((-1.00, .75), (-1.00, 1.77), (-.98, 2.29), (-.72, 2.40), 22)
    right_inner = [(-x, z) for x, z in reversed(left_inner)]
    outline = [(-1.45, 0.0)] + left_outer + [(-.34, 1.93), (0, 1.28), (.34, 1.93), (.73, 3.00)] \
        + right_outer + [(1.45, 0.0), (1.00, 0.0)] + list(reversed(right_inner)) \
        + [(.30, 1.60), (0, 1.02), (-.30, 1.60)] + left_inner + [(-1.00, 0.0)]
    clean = []
    for p in outline:
        if not clean or (abs(p[0] - clean[-1][0]) + abs(p[1] - clean[-1][1]) > .0001):
            clean.append(p)
    sx = width / 2.90
    sz = height / 3.00
    return [(cx + x * sx, base_z + z * sz) for x, z in clean]

def prism_from_xz(name, pts, y0, y1, mat, col, evidence, estimated=True):
    n = len(pts)
    verts = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    me = bpy.data.meshes.new(name + '_mesh')
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    COL[col].objects.link(o)
    me.materials.append(mat)
    return tag(o, name, evidence, estimated)

# =========================================================
# 08_ENVIRONMENT_FUJI - user-mandated backdrop (exported)
# =========================================================
w = B['width']; d = B['depth']; eh = B['eave_height']

# Wet asphalt foreground plane.
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 900, 0))
gnd = bpy.context.object
gnd.name = 'Ground_wet_asphalt_foreground'
gnd.scale = (4200, 4200, 1)
bpy.ops.object.transform_apply(scale=True)
gnd.data.materials.append(MAT['ground'])
move_to(gnd, 'env')
tag(gnd, gnd.name, 'REF_USER wet reflective forecourt', False)

# --- Mt. Fuji: three stacked cone segments sharing one cloud-noise displace
# (global coords keep the seams continuous). Visible slope half-angle ~25.6deg
# matches the photo's apparent profile; the foot disappears into the mist band. ---
zm = FJ['mist_z']            # mist line height
rm = FJ['r_mist']            # cone radius at the mist line
hv = FJ['h_vis']             # visible height above the mist line
summit_z = zm + hv
z_snow = zm + hv * (1 - FJ['snow_frac'])
r_snow = rm * FJ['snow_frac']
noise = bpy.data.textures.new('Fuji_ridge_noise', 'CLOUDS')
noise.noise_scale = 140.0

def displace_ridge(obj, strength):
    mod = obj.modifiers.new('Ridge_displace', 'DISPLACE')
    mod.texture = noise
    mod.texture_coords = 'GLOBAL'
    mod.mid_level = .5
    mod.strength = strength

# Dark foothill cone: flares down to the ground plane so no underside cap of
# the visible cone shows above the mist; its top edge tucks under the cloud sea.
foot = cone('Fuji_foothill_below_mist', (FJ['cx'], FJ['cy'], zm / 2),
            1531.0, rm, zm, MAT['fuji_foot'], 'env', vertices=128,
            evidence='REF_USER dark foothill layer under the cloud sea; user-mandated backdrop')
body = cone('Fuji_slope_above_mist', (FJ['cx'], FJ['cy'], zm + (z_snow - zm) / 2),
            rm, r_snow, z_snow - zm, MAT['fuji_body'], 'env', vertices=128,
            evidence='REF_USER blue-grey mountain slope fading into dusk')
cap = cone('Fuji_snowcap_upper_cone', (FJ['cx'], FJ['cy'], z_snow + (summit_z - z_snow) / 2),
           r_snow, .5, summit_z - z_snow, MAT['fuji_snow'], 'env', vertices=128,
           evidence='REF_USER snow-capped summit with ridge shading')
for seg in (foot, body, cap):
    displace_ridge(seg, 70.0)

# --- cloud sea: billboard walls with a vertical-alpha gradient texture
# (mist_gradient.png) - reads as a thick mist band at the mountain foot from
# the low hero camera, and exports cleanly to glTF (baseColorTexture alpha). ---
mist_img = bpy.data.images.load(os.path.join(ROOT, 'src', 'mist_gradient.png'))
mist_mat = bpy.data.materials.new('ATMOS_cloudsea_billboard')
mist_mat.use_nodes = True
mp = next(n for n in mist_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
nt = mist_mat.node_tree
tex_n = nt.nodes.new('ShaderNodeTexImage')
tex_n.image = mist_img
tex_n.interpolation = 'Linear'
nt.links.new(tex_n.outputs['Color'], mp.inputs['Base Color'])
# 模型查看器以贴图 alpha 为主导：乘一个低系数，避免整面云海在 Web 端变成白色幕布
alpha_mul = nt.nodes.new('ShaderNodeMath')
alpha_mul.operation = 'MULTIPLY'
alpha_mul.inputs[1].default_value = .06
nt.links.new(tex_n.outputs['Alpha'], alpha_mul.inputs[0])
nt.links.new(alpha_mul.outputs[0], mp.inputs['Alpha'])
mp.inputs['Emission Color'].default_value = (*srgb('#8AA0C4'), 1)
mp.inputs['Emission Strength'].default_value = .04
mp.inputs['Roughness'].default_value = .9
mist_mat.blend_method = 'BLEND'
mist_mat.diffuse_color = (*srgb('#8AA0C4'), .6)

def mist_wall(name, loc, w_, h_):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = (math.pi / 2, 0, 0)   # stand upright, face -Y
    o.dimensions = (w_, h_, 1)               # local y spans world Z after rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.data.materials.append(mist_mat)
    move_to(o, 'env')
    return tag(o, name, 'REF_USER cloud sea hiding the mountain foot', False)

mist_wall('Fuji_cloudsea_wall_back', (FJ['cx'], 2050, 365), 2900, 420)
mist_wall('Fuji_cloudsea_wall_front', (FJ['cx'], 1720, 330), 3200, 340)

# --- far hills silhouettes left and right on the horizon. ---
for i, hs in enumerate(CONFIG['far_hills']):
    cone('Far_hill_silhouette_%02d' % (i + 1), (hs['x'], hs['y'], hs['h'] / 2),
         hs['r'], 1.0, hs['h'], MAT['far_hill'], 'env', vertices=48,
         evidence='REF_USER low hills on both flanks')

# --- two conifer silhouettes at the left edge (photo: dark spruce shapes). ---
for i, t in enumerate(CONFIG['trees']):
    tx, ty, th, tr = t['x'], t['y'], t['h'], t['r']
    cyl('Conifer_%02d_trunk' % (i + 1), (tx, ty, th * .16), .09 * th * .35,
        th * .34, MAT['tree'], 'env', vertices=12,
        evidence='REF_USER conifer silhouettes on the left flank')
    tiers = 4
    for k in range(tiers):
        z0 = th * (.22 + .62 * k / tiers)
        h_tier = th * .68 / tiers * 1.5
        r_tier = tr * (1 - .62 * k / tiers)
        cone('Conifer_%02d_tier_%02d' % (i + 1, k + 1),
             (tx, ty, z0 + h_tier / 2), r_tier, .02, h_tier,
             MAT['tree'], 'env', vertices=24,
             evidence='REF_USER conifer silhouette layers')

# =========================================================
# building: single-storey roadside store, black fascia roof band
# =========================================================
# roof slab + fascia band around all sides (photo: thin dark eave, deep shadow).
box('Roof_slab_black', (0, d / 2, eh + B['roof_thick'] / 2),
    (w + 2 * B['fascia_overhang'], d + 2 * B['fascia_overhang'], B['roof_thick']),
    MAT['roof'], 'shell', .02, 'REF_USER thin black eave slab')
fy = -B['fascia_overhang'] / 2
box('Fascia_front_band', (0, fy, eh - .08),
    (w + 2 * B['fascia_overhang'], .22, .55), MAT['band'], 'shell', .015,
    'REF_USER dark fascia above the glazing')
for sx_, sy_, dims_ in [(-w / 2 - .06, d / 2, (.22, d + .4, .55)),
                        (w / 2 + .06, d / 2, (.22, d + .4, .55)),
                        (0, d + .06, (w + .4, .22, .55))]:
    box('Fascia_side_or_rear_band_%+.1f_%+.1f' % (sx_, sy_), (sx_, sy_, eh - .08),
        dims_, MAT['band'], 'shell', .015, 'REF_USER eave band wraps the volume')

# side/rear walls and floor (unseen in photo; inferred completion).
box('Store_left_end_wall', (-w / 2 + .1, d / 2, eh / 2), (.2, d, eh),
    MAT['band'], 'shell', .02, 'unseen side simplified')
box('Store_right_end_wall', (w / 2 - .1, d / 2, eh / 2), (.2, d, eh),
    MAT['band'], 'shell', .02, 'unseen side simplified')
box('Store_rear_wall', (0, d - .1, eh / 2), (w, .2, eh),
    MAT['band'], 'shell', .02, 'unseen rear simplified')
box('Store_floor_slab', (0, d / 2, .05), (w, d, .1), MAT['band'], 'shell',
    evidence='inferred slab')

# ---------- glazing band: dark glass, warm interior behind ----------
gx0, gx1 = FA['glass_x']
gz0, gz1 = FA['glass_z']
box('Storefront_glass_band', ((gx0 + gx1) / 2, .05, (gz0 + gz1) / 2),
    (gx1 - gx0, .06, gz1 - gz0), MAT['glass'], 'glass',
    evidence='REF_USER continuous glazing with warm interior glow')
n_mull = int((gx1 - gx0) / FA['mullion_step'])
for i in range(n_mull + 1):
    mx = gx0 + i * ((gx1 - gx0) / n_mull)
    box('Storefront_mullion_%02d' % (i + 1), (mx, .05, (gz0 + gz1) / 2),
        (.09, .14, gz1 - gz0), MAT['frame'], 'glass', .008,
        'REF_USER vertical mullion rhythm')
for zz in [gz0 + .04, gz1 - .04]:
    box('Storefront_horizontal_rail_z%.2f' % zz, ((gx0 + gx1) / 2, .05, zz),
        (gx1 - gx0, .14, .09), MAT['frame'], 'glass', .008,
        'REF_USER top/bottom glazing rails')

# warm interior: back panel + counter + table silhouettes (abstract, no people)
box('Interior_warm_backwall', (0, d * .55, (gz0 + gz1) / 2 + .4),
    (w - 3.2, .12, gz1 - gz0 - .2), MAT['interior_glow'], 'glass',
    evidence='REF_USER warm interior glow across the full width')
box('Interior_counter_silhouette', (3.0, d * .38, 1.15), (9.5, 1.1, 1.1),
    MAT['interior_deep'], 'glass', .02,
    'REF_USER dark counter line inside the glazing (silhouette only, inferred)')
for i, tx in enumerate([-8.6, -6.4, -4.2, 8.6]):
    box('Interior_table_silhouette_%02d' % (i + 1), (tx, d * .42, .78),
        (1.1, 1.1, .08), MAT['interior_deep'], 'glass',
        evidence='dining-room furniture silhouette (inferred, REF_USER blur)')
    cyl('Interior_table_leg_%02d' % (i + 1), (tx, d * .42, .37), .05, .74,
        MAT['interior_deep'], 'glass', vertices=10,
        evidence='table leg (inferred)')

# ceiling strip of warm downlights behind the glass (reads as bright line).
box('Interior_ceiling_lightstrip', (0, d * .3, gz1 - .22), (w - 3.4, .1, .06),
    MAT['interior_glow'], 'glass',
    evidence='REF_USER bright ceiling line inside the glazing')

# plinth / kick base under the glazing.
box('Storefront_plinth', ((gx0 + gx1) / 2, .12, FA['plinth_h'] / 2),
    (w - 2 * FA['left_solid_width'], .3, FA['plinth_h']), MAT['band'], 'facade',
    .01, 'REF_USER dark kick base')

# left solid end panel (photo: left bay reads darker/solid).
box('Storefront_left_solid_panel', (-w / 2 + FA['left_solid_width'] / 2, .1, eh / 2),
    (FA['left_solid_width'], .3, eh), MAT['band'], 'facade', .015,
    'REF_USER darker left bay')

# entrance double door (position inferred from darker mullion cluster).
dxc0, dxc1 = FA['door']['x0'], FA['door']['x1']
dcx = (dxc0 + dxc1) / 2
box('Entrance_door_frame_head', (dcx, .02, gz1 - .12), (dxc1 - dxc0, .16, .1),
    MAT['frame'], 'glass', .008, 'REF_USER darker door bay (position inferred)')
box('Entrance_door_center_mullion', (dcx, .02, (gz0 + gz1) / 2), (.07, .14, gz1 - gz0),
    MAT['frame'], 'glass', .008, 'door center stile (inferred)')

# ---------- roof-top sign band: black board, red M box, white wordmark ----------
bw, bh, bd = RS['width'], RS['height'], RS['depth']
bcz = RS['center_z']
box('Rooftop_sign_board_black', (0, -.18, bcz), (bw, bd, bh), MAT['band_lit'],
    'sign', .02, 'REF_USER black rooftop sign board')
rbw = RS['red_box']['width']
rbx = RS['red_box']['center_x']
box('Rooftop_sign_red_M_panel', (rbx, -.40, bcz), (rbw, .12, bh * .82),
    MAT['red_lit'], 'sign', .012, 'REF_USER red M panel at the left end')
mpts = m_outline(rbx, bcz - bh * .38, RS['m_width'], bh * .62)
M_roof = prism_from_xz('Rooftop_golden_M_lit', mpts, -.48, -.42, MAT['gold_lit'],
                       'sign', 'REF_USER golden M on red panel', False)
bevel(M_roof, .012, 2)
text_obj('Rooftop_wordmark_McDonalds', "McDonald's", RS['wordmark_x'], -.40, bcz,
         RS['wordmark_size'], MAT['white_lit'], extrude=.028,
         evidence="REF_USER white 'McDonald's' wordmark on the black board")

# small roof-mounted M board at the right end of the roof slab.
rmx = CONFIG['roof_m_sign']['x']
rmz = CONFIG['roof_m_sign']['top_z']
rms = CONFIG['roof_m_sign']['size']
box('Roofend_small_red_board', (rmx, -.30, rmz), (rms * 1.25, .1, rms),
    MAT['red_lit'], 'sign', .01, 'REF_USER small red M board on the right roof end')
mpts_small = m_outline(rmx, rmz - rms * .42, rms * .8, rms * .66)
M_small = prism_from_xz('Roofend_small_golden_M', mpts_small, -.37, -.34,
                        MAT['gold_lit'], 'sign', 'REF_USER small golden M', False)
bevel(M_small, .008, 2)

# =========================================================
# freestanding pole sign: gold M on red board + OPEN 24 HOURS
# =========================================================
px, py = PS['x'], PS['y']
pw = PS['pole_w']
cyl('Pole_sign_grey_column', (px, py, PS['pole_top_z'] / 2), pw / 2,
    PS['pole_top_z'], MAT['pole'], 'sign', vertices=20,
    evidence='REF_USER slender grey pole sign right of the store')
rb = PS['red_board']
box('Pole_red_board', (px, py, rb['z']), (rb['w'], .3, rb['h']),
    MAT['red_lit'], 'sign', .02, 'REF_USER red McDonalds board on the pole')
mpts_pole = m_outline(px, rb['z'] + rb['h'] / 2 + .12, PS['m_width'], PS['m_width'] * 1.02)
M_pole = prism_from_xz('Pole_golden_M_lit', mpts_pole, py - .17, py - .13,
                       MAT['gold_lit'], 'sign', 'REF_USER golden M atop the pole', False)
bevel(M_pole, .015, 2)
text_obj('Pole_wordmark_McDonalds', "McDonald's", px, py - .17, rb['z'], .62,
         MAT['white_lit'], extrude=.022,
         evidence="REF_USER white wordmark on the red board")
ob = PS['open_board']
box('Pole_open24_board', (px, py, ob['z']), (ob['w'], .24, ob['h']),
    MAT['open_lit'], 'sign', .015, 'REF_USER black OPEN 24 HOURS board')
text_obj('Pole_open24_text', 'OPEN 24 HOURS', px, py - .14, ob['z'], .26,
         MAT['white_lit'], extrude=.012,
         evidence='REF_USER OPEN 24 HOURS legend (note: official JP site lists 7:00-23:00; user photo wins)')

# pole base collar (grounding detail).
cyl('Pole_base_collar', (px, py, .12), pw * .8, .24, MAT['pole'], 'sign',
    vertices=20, evidence='pole base collar (inferred)')

# =========================================================
# 07_LIGHTING_STORE (exported; spot/point/sun only - no AREA, KHR has none)
# =========================================================
def spot(name, loc, energy, color, size_rad, target, blend=.8):
    data = bpy.data.lights.new(name, 'SPOT')
    data.energy = energy
    data.color = color
    data.spot_size = math.radians(size_rad)
    data.spot_blend = blend
    o = bpy.data.objects.new(name, data)
    COL['light'].objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()
    o['light_role'] = 'store_photo_lighting'
    return o

def point(name, loc, energy, color):
    data = bpy.data.lights.new(name, 'POINT')
    data.energy = energy
    data.color = color
    o = bpy.data.objects.new(name, data)
    COL['light'].objects.link(o)
    o.location = loc
    o['light_role'] = 'store_photo_lighting'
    return o

def sun(name, loc, energy, color, target=(0, 0, 0)):
    data = bpy.data.lights.new(name, 'SUN')
    data.energy = energy
    data.color = color
    data.angle = math.radians(6)
    o = bpy.data.objects.new(name, data)
    COL['light'].objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()
    o['light_role'] = 'dusk_environment_lighting'
    return o

warm = srgb(LC['interior_warm_light'])
# glTF 的 KHR_lights_punctual 会把 Blender 瓦特换算成 cd/lux（×683 量级），
# 而 three.js / model-viewer 直接拿这个值当光强用 → 整场景严重过曝。
# 这里统一缩放，使近场（3-5m）落在几十 lux 的合理区间。
LS = 0.02
if THEME == 'night':
    # Warm interior wash (the glow seen through the glazing).
    spot('Interior_warm_wash_left', (-5, 4.0, 3.7), 900 * LS, warm, 150, (-5, -1, 1.4))
    spot('Interior_warm_wash_right', (5, 4.0, 3.7), 900 * LS, warm, 150, (5, -1, 1.4))
    # Sign band wash so the board face lifts off the sky.
    spot('Signband_wash', (0, -5.5, 8.2), 420 * LS, warm, 130, (0, -.3, 5.3))
    # Entrance spill onto the wet forecourt (photo: warm reflections).
    point('Entrance_spill_glow', (dcx, -1.2, 3.3), 260 * LS, warm)
    point('Interior_core_glow', (0, 4.5, 2.2), 420 * LS, warm)
    # Pole sign ambient points (boards are emissive; points add halo on the pole).
    point('Pole_sign_glow', (px, py - .9, rb['z']), 90 * LS, srgb('#FF6A4A'))
    # Dusk environment: cool ambient sun + warm ghost of the sunset from the right.
    sun('Dusk_cool_ambient', (-260, 380, 460), 0.8 * LS, srgb(LC['dusk_ambient']))
    sun('Sunset_warm_ghost', (900, 500, 60), LC['dawn_rim_strength'] * .12 * LS,
        srgb(LC['sun_ghost']), (-100, 900, 120))
else:
    # 日间：门店灯光全部关闭，不导出任何 punctual 灯。
    # 主光完全交给 model-viewer 的 neutral 环境光（与沙面/丽都模型口径一致），
    # 这样白天是「自然光、无人工照明」的干净状态。
    pass

# =========================================================
# metadata, world, studio, cameras
# =========================================================
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'
scene['model_scope'] = 'Dusk scene: single-storey store + user-mandated Mt.Fuji backdrop, mist, far hills, conifers, wet forecourt'
scene['dimensional_accuracy'] = 'Photo-estimated proportions; not surveyed; Fuji scale is a visual match of an artistic photo, not geographic'
scene['reference_photos'] = 'REF_USER (user-supplied dusk photo); identity cross-check: 139 Fujiyoshida store archive photos'
scene['lighting_basis'] = 'REF_USER dusk glow: warm interior, lit signage boards, cool dusk ambient, warm sunset ghost right'
scene['source_script'] = 'src/build_fuji.py'
scene['config'] = 'src/fuji_config.json'

world = bpy.data.worlds.new('Fuji_dusk_world')
scene.world = world
world.use_nodes = True
wnodes = world.node_tree
wnodes.nodes.clear()
tc = wnodes.nodes.new('ShaderNodeTexCoord')
sep = wnodes.nodes.new('ShaderNodeSeparateXYZ')
ramp = wnodes.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = .08
ramp.color_ramp.elements[0].color = (*srgb(C['sky_horizon']), 1)
ramp.color_ramp.elements[1].position = .62
ramp.color_ramp.elements[1].color = (*srgb(C['sky_top']), 1)
# sunset glow on the right, fading with elevation (photo: warm dusk gradient)
mr_x = wnodes.nodes.new('ShaderNodeMapRange')
mr_x.inputs['From Min'].default_value = 0.0
mr_x.inputs['From Max'].default_value = 0.8
mr_x.inputs['To Min'].default_value = 0.0
mr_x.inputs['To Max'].default_value = 0.75
abs_z = wnodes.nodes.new('ShaderNodeMath')
abs_z.operation = 'ABSOLUTE'
mr_z = wnodes.nodes.new('ShaderNodeMapRange')
mr_z.inputs['From Min'].default_value = 0.0
mr_z.inputs['From Max'].default_value = 0.30
mr_z.inputs['To Min'].default_value = 1.0
mr_z.inputs['To Max'].default_value = 0.0
mult = wnodes.nodes.new('ShaderNodeMath')
mult.operation = 'MULTIPLY'
mix = wnodes.nodes.new('ShaderNodeMixRGB')
mix.blend_type = 'MIX'
mix.inputs[2].default_value = (*srgb(C['sky_glow']), 1)
bg = wnodes.nodes.new('ShaderNodeBackground')
bg.inputs[1].default_value = 1.0
out = wnodes.nodes.new('ShaderNodeOutputWorld')
mapz = wnodes.nodes.new('ShaderNodeMapRange')
mapz.inputs['From Min'].default_value = -0.1
mapz.inputs['From Max'].default_value = 0.7
wnodes.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
wnodes.links.new(sep.outputs['Z'], mapz.inputs['Value'])
wnodes.links.new(mapz.outputs['Result'], ramp.inputs['Fac'])
wnodes.links.new(sep.outputs['X'], mr_x.inputs['Value'])
wnodes.links.new(sep.outputs['Z'], abs_z.inputs[0])
wnodes.links.new(abs_z.outputs[0], mr_z.inputs['Value'])
wnodes.links.new(mr_x.outputs['Result'], mult.inputs[0])
wnodes.links.new(mr_z.outputs['Result'], mult.inputs[1])
wnodes.links.new(ramp.outputs['Color'], mix.inputs[1])
wnodes.links.new(mult.outputs[0], mix.inputs[0])
wnodes.links.new(mix.outputs['Color'], bg.inputs['Color'])
wnodes.links.new(bg.outputs['Background'], out.inputs['Surface'])

def camera(name, loc, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start = .1
    data.clip_end = 9000   # Mt. Fuji sits ~2600m away; default 100m clips it
    o = bpy.data.objects.new(name, data)
    COL['studio'].objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()
    return o

CAMS = {k: camera('CAM_%s' % k, v['loc'], v['target'], v['lens'])
        for k, v in CONFIG['cameras'].items()}
CAMS['hero']['hero_match'] = '构图匹配用户参考照片（单层店居中、富士山背景、立柱牌右侧、双树左侧）'

# studio ground slightly below the wet forecourt for previews
box('Studio_shadow_ground', (0, 0, -.16), (60, 60, .1), MAT['studio_ground'],
    'studio', evidence='preview only')

scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.render.resolution_x = 1600
scene.render.resolution_y = 760
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.camera = CAMS['hero']

t = bpy.data.texts.new('READ_ME_模型说明')
t.write('富士山下的麦当劳｜%s场景模型（富士山背景为用户指定不可移除部分）\n\n'
        '单位：米。尺寸均为照片推定，非实测。\n'
        '01/02/04/05/08 集合为建筑、招牌与富士山环境；07 为灯光（导出）；\n'
        '90 为预览影棚，导出不含。富士山/云雾/远山/针叶树/湿地坪在 08，随模型导出。\n'
        '灯光依据：%s。\n'
        '文字在 .blend 中保持可编辑；脚本与 fuji_config.json 可复建。\n'
        '昼夜两版由 --theme day / night 分别导出，几何完全一致，仅材质与灯光不同。\n'
        % ('日间' if THEME == 'day' else '黄昏',
           '日间自然光（门店灯光关闭）' if THEME == 'day' else '用户参考照片（黄昏蓝调+店内暖光+发光招牌）'))
bpy.ops.file.pack_all()
blend_path = os.path.join(MODELS, BLEND_NAME)
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

# ---------- exports ----------
bpy.ops.object.select_all(action='DESELECT')
for o in list(COL['sign'].objects):
    if o.type in {'FONT', 'CURVE'}:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.convert(target='MESH')
        o.select_set(False)

EXPORT_KEYS = ['shell', 'facade', 'glass', 'sign', 'env']
model_objects = []
for key in EXPORT_KEYS:
    model_objects.extend([o for o in COL[key].objects if o.type == 'MESH'])
light_objects = [o for o in COL['light'].objects if o.type == 'LIGHT']
bpy.ops.object.select_all(action='DESELECT')
for o in model_objects + light_objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = model_objects[0]

bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, GLB_NAME),
    export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
    export_materials='EXPORT', export_extras=True, export_lights=True)
if THEME == 'night':
    bpy.ops.wm.obj_export(filepath=os.path.join(MODELS, 'Fuji_McDonalds.obj'),
        export_selected_objects=True, apply_modifiers=True,
        export_materials=True, path_mode='COPY')
    try:
        bpy.ops.export_scene.fbx(filepath=os.path.join(MODELS, 'Fuji_McDonalds.fbx'),
            use_selection=True, use_mesh_modifiers=True, add_leaf_bones=False)
    except Exception as e:
        print('FBX export warning:', e)

# ---------- previews (dusk state is the only photo-evidenced state) ----------
if '--no-render' not in sys.argv:
    for o in COL['studio'].objects:
        if o.type == 'LIGHT':
            o.hide_render = True
    for o in COL['light'].objects:
        o.hide_render = False
    for key in CONFIG['cameras']:
        scene.camera = CAMS[key]
        scene.render.filepath = os.path.join(PREVIEWS, 'Fuji_0%s_%s%s.png'
                                             % (list(CONFIG['cameras']).index(key) + 1, key,
                                                '_day' if THEME == 'day' else ''))
        bpy.ops.render.render(write_still=True)

# ---------- manifest ----------
mesh_stats = {'vertices': 0, 'polygons': 0,
              'objects': len(model_objects), 'lights': len(light_objects),
              'collections': []}
for o in model_objects:
    if o.type == 'MESH':
        mesh_stats['vertices'] += len(o.data.vertices)
        mesh_stats['polygons'] += len(o.data.polygons)
for key in EXPORT_KEYS + ['light']:
    mesh_stats['collections'].append({'name': COL[key].name,
                                      'objects': len(COL[key].objects)})
mesh_stats['dimensions_m'] = {'store_width': w, 'store_depth': d,
                              'eave_height': eh,
                              'fuji_visible_height': hv, 'fuji_radius_at_mist': rm,
                              'fuji_distance': FJ['cy']}
mesh_stats['scale_note'] = CONFIG['scale_basis']
mesh_stats['source_photos'] = scene['reference_photos']
mesh_stats['scene_type'] = 'SCENE (building + user-mandated landscape backdrop)'
mesh_stats['exports'] = ['Fuji_McDonalds.blend', 'Fuji_McDonalds.glb',
                         'Fuji_McDonalds_day.glb',
                         'Fuji_McDonalds.obj', 'Fuji_McDonalds.fbx']
mesh_stats['theme'] = THEME
if THEME == 'day':
    json.dump(mesh_stats, open(os.path.join(MODELS, 'model_manifest_day.json'), 'w',
                               encoding='utf-8'), ensure_ascii=False, indent=2)
else:
    json.dump(mesh_stats, open(os.path.join(MODELS, 'model_manifest.json'), 'w',
                               encoding='utf-8'), ensure_ascii=False, indent=2)
print('BUILD_COMPLETE', json.dumps(mesh_stats, ensure_ascii=False))
