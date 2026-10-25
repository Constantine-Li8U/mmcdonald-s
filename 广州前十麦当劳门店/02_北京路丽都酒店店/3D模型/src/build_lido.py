# -*- coding: utf-8 -*-
"""Parametric architectural model: McDonald's at Lido Hotel, Beijing Road, Guangzhou.

Run with Blender 4.5 LTS:
  blender --background --python src/build_lido.py
  blender --background --python src/build_lido.py -- --no-render

All dimensions are photo-derived estimates, not surveyed measurements.
Scope: only the two-storey hotel podium used by McDonald's; the hotel tower
is not discernible in the photos and is not modelled.

Lighting is a first-class deliverable: every luminous element is taken from
the store's own photos (night facade EXT_01, day facade EXT_02/EXT_03,
dessert-station lightboxes SIGN_01, McCafe warm wall CNT_02, level-2 seating
SEAT_01..04). Two lighting states are kept in the .blend:
  DAY   - neutral studio softboxes (collection 90, excluded from export)
  NIGHT - store's own lights only (collection 07, exported with the model)
"""
import bpy
import math
import json
import os
import sys
from mathutils import Vector, Quaternion, Euler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(ROOT, 'src', 'lido_config.json'), encoding='utf-8'))
MODELS = os.path.join(ROOT, 'models')
PREVIEWS = os.path.join(ROOT, 'previews')
os.makedirs(MODELS, exist_ok=True)
os.makedirs(PREVIEWS, exist_ok=True)

B = CONFIG['building']
S = CONFIG['storefront']
L2 = CONFIG['level2']
BP = CONFIG['black_panel']
LC = CONFIG['lighting']

# ---------- scene and organization ----------
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
    'canopy': collection('03_CANOPY_AND_BANDS'),
    'glass': collection('04_GLAZING_AND_DOORS'),
    'sign': collection('05_SIGNAGE'),
    'steps': collection('06_ENTRANCE_STEPS'),
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

def material(name, color, rough=0.5, metal=0.0, transmission=0.0,
             emission=0.0, emission_color=None):
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
        p.inputs['Emission Color'].default_value = (*srgb(emission_color or color), 1)
        p.inputs['Emission Strength'].default_value = emission
    return m

C = CONFIG['materials']
MAT = {
    'podium': material('CLAD_dark_charcoal_podium', C['podium_dark'], .62),
    'slat': material('WOOD_warm_brown_slats', C['wood_slat'], .58),
    'slat_dark': material('WOOD_slat_shadow_gaps', C['wood_slat_dark'], .7),
    'canopy': material('CLAD_warm_white_canopy', C['canopy_white'], .55),
    'glass': material('GLASS_dark_shopfront', '#26323A', .14, .06, .65),
    'frame': material('METAL_dark_frames', C['frame_dark'], .34, .68),
    'gold': material('SIGN_McDonalds_golden_yellow', C['mcd_yellow'], .3, .3),
    # Luminous materials: emission is the photo-evidenced lit state of the sign.
    'gold_lit': material('SIGN_M_lit_night', C['mcd_yellow'], .3, .1,
                         emission=LC['m_glow_strength']),
    'red': material('SIGN_McDonalds_red', C['mcd_red'], .5),
    'red_lit': material('SIGN_red_box_lit_night', C['mcd_red'], .45,
                        emission=LC['red_box_glow'] * .35),
    'white': material('SIGN_warm_white_letters', C['letter_white'], .34),
    'white_lit': material('SIGN_McCafe_script_lit', C['letter_white'], .34,
                          emission=LC['mccafe_script_glow']),
    'warm': material('INTERIOR_warm_back_panel', C['interior_warm'], .7,
                     emission=1.1, emission_color=LC['interior_warm_light']),
    'warm_lit': material('INTERIOR_level2_warm_glow', C['interior_warm'], .65,
                         emission=2.6, emission_color=LC['interior_warm_light']),
    'cyan_lit': material('LIGHTBOX_menu_cyan_glow', '#2E6E86', .4,
                         emission=LC['lightbox_strength'],
                         emission_color=LC['lightbox_cyan']),
    'down_lit': material('CANOPY_downlight_warm_glow', '#FFE4B0', .35,
                         emission=5.0, emission_color=LC['downlight_warm']),
    'hotel_lit': material('SIGN_Lido_hotel_letters_lit', '#D9B98A', .4,
                          emission=LC['hotel_letters_glow']),
    'roof': material('ROOF_flat_dark_membrane', C['roof'], .88),
    'step': material('STEP_grey_stone', C['step'], .8),
    'ground': material('STUDIO_neutral_ground', '#E6E3DC', .85),
    # --- dessert-station cabinet & entrance door furniture ---
    'cabinet': material('CABINET_lightbox_white_powdercoat', '#EAE8E2', .5, .08),
    'steel': material('METAL_brushed_stainless_pull_handles', '#C7CBCE', .26, .92),
    'steel_dark': material('METAL_handle_fixings_dark', '#565B5F', .42, .85),
    'gasket': material('SEAM_rubber_gasket_lines', '#1E2124', .8),
    'kick': material('PLATE_stainless_kick_wear', '#A9ADAF', .38, .8),
    'screen_hi': material('SCREEN_menu_highlight_band', '#C8ECF8', .3,
                          emission=3.0, emission_color='#C8ECF8'),
    'screen_warm': material('SCREEN_menu_product_thumb', '#F3E2C8', .4,
                            emission=2.0, emission_color='#F3E2C8'),
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

def cyl(name, loc, radius, depth, mat, col, rot=(0, 0, 0), vertices=24,
        evidence='photo-derived', estimated=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                        location=loc, rotation=rot,
                                        vertices=vertices)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
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

def prism_from_xz(name, pts, y0, y1, mat, col, evidence, estimated=True):
    n = len(pts)
    verts = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    return mesh_obj(name, verts, faces, mat, col, evidence, estimated)

FONT = bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')
FONT_ITALIC = bpy.data.fonts.load('C:/Windows/Fonts/arialbi.ttf')
FONT_CN = bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')

def text_obj(name, body, x, y, z, size, mat, font=None, extrude=.012,
             evidence='photo signage'):
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
    o.rotation_quaternion = Euler((math.pi/2, 0, 0)).to_quaternion()
    cu.materials.append(mat)
    return tag(o, name, evidence, False)

# ---------- golden arches M outline (shared series asset) ----------
def cubic(p0, p1, p2, p3, n=18):
    out = []
    for i in range(n+1):
        t = i/n; u = 1-t
        out.append((u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0],
                    u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]))
    return out

def m_outline(cx, base_z, width, height):
    left_outer = cubic((-1.45,.80),(-1.45,2.02),(-1.17,2.91),(-.73,3.00),24)
    right_outer = [(-x,z) for x,z in reversed(left_outer)]
    left_inner = cubic((-1.00,.75),(-1.00,1.77),(-.98,2.29),(-.72,2.40),22)
    right_inner = [(-x,z) for x,z in reversed(left_inner)]
    outline = [(-1.45,0.0)] + left_outer + [(-.34,1.93),(0,1.28),(.34,1.93),(.73,3.00)] \
        + right_outer + [(1.45,0.0),(1.00,0.0)] + list(reversed(right_inner)) \
        + [(.30,1.60),(0,1.02),(-.30,1.60)] + left_inner + [(-1.00,0.0)]
    clean = []
    for p in outline:
        if not clean or (abs(p[0]-clean[-1][0])+abs(p[1]-clean[-1][1]) > .0001):
            clean.append(p)
    sx = width/2.90
    sz = height/3.00
    return [(cx+x*sx, base_z+z*sz) for x, z in clean]

# ---------- host podium shell (two storeys only; tower not modelled) ----------
w = B['width']; d = B['depth']
gft = B['ground_floor_top']; l2t = B['level2_top']; pt = B['parapet_top']
sx0, sx1 = S['slat_strip']
e0, e1 = S['entrance']

# Structural back wall of the podium, set deep so the lit interior cavity
# stays visible through the glazing (photos show a glowing interior at night).
box('Podium_deep_back_wall', (0, 6.2, pt/2), (w, .32, pt), MAT['podium'], 'shell',
    evidence='EXT_02;EXT_03;interior cavity inferred')
# Left / right / rear / roof inferred completion.
box('Host_left_party_wall', (-w/2+.16, d/2, pt/2), (.32, d, pt), MAT['podium'],
    'shell', .02, 'unseen side simplified')
box('Host_right_party_wall', (w/2-.16, d/2, pt/2), (.32, d, pt), MAT['podium'],
    'shell', .02, 'unseen side simplified')
box('Host_rear_plain_wall', (0, d-.16, pt/2), (w, .32, pt), MAT['podium'],
    'shell', .02, 'unseen rear simplified')
for z, label in [(.12, 'Ground_floor_slab'), (gft, 'Level_02_slab'), (l2t, 'Roof_slab')]:
    box(label, (0, d/2, z), (w-.55, d-.35, .20), MAT['podium'], 'shell',
        evidence='inferred floor slab')
box('Flat_roof_inferred', (0, d/2, pt+.05), (w, d, .16), MAT['roof'], 'shell',
    .02, 'unseen roof simplified')

# ---------- ground floor: piers, header, glazing ----------
piers = [-7.5+0.0, sx1, e0, e1, 7.5]
for i, px in enumerate([sx0, sx1, e0, e1]):
    pass
# Vertical piers between storefront sections (dark charcoal).
for i, px in enumerate([sx1, e0, e1]):
    box('Storefront_pier_%02d' % i, (px, .05, gft/2), (.38, .5, gft), MAT['podium'],
        'facade', .02, 'EXT_02;EXT_03')
# Right end pier.
box('Storefront_right_end_pier', (7.5-.19, .05, gft/2), (.38, .5, gft),
    MAT['podium'], 'facade', .02, 'EXT_01;EXT_02')
# Header band above ground-floor glazing (behind red sign box).
box('Ground_floor_header_band', ((sx1+7.5)/2, .08, (3.05+gft)/2),
    (7.5-sx1, .44, gft-3.05), MAT['podium'], 'facade', .02, 'EXT_02;EXT_03')

def glazing(label, x0, x1, z0=0.18, z1=3.05, y=0.02, lit_mat=None):
    cx = (x0+x1)/2
    ww = x1-x0
    box(label+'_dark_glazing', (cx, y, (z0+z1)/2), (ww-.12, .06, z1-z0),
        MAT['glass'], 'glass', evidence='EXT_01;EXT_02;EXT_03')
    for dx in [x0+.05, x1-.05]:
        box(label+'_side_frame', (dx, y+.02, (z0+z1)/2), (.09, .14, z1-z0),
            MAT['frame'], 'glass', .01, 'EXT_02;EXT_03')
    for z in [z0+.03, z1-.03]:
        box(label+'_horizontal_frame', (cx, y+.02, z), (ww, .14, .08),
            MAT['frame'], 'glass', .01, 'EXT_02;EXT_03')
    return cx, ww

# Window glazing behind the dessert station (the kiosk stands in front of it).
dwx0, dwx1 = S['dessert_window']
glazing('Dessert_window', dwx0, dwx1)
# ---------- freestanding dessert station (SIGN_01 photo reference) ----------
# Photo: a white powder-coated cabinet column on the sidewalk in front of the
# left storefront; dark plinth, three stacked illuminated menu screens with
# visible frames and gasket seams, corner trims and a shallow top cap.
dscx = (dwx0 + dwx1) / 2            # -2.75, centred on the dessert window
ds_w, ds_d = 1.60, .60              # cabinet 1.6m wide x 0.6m deep
ds_y = -.38                         # back of cabinet nearly touches glazing
ds_h0, ds_h1 = .16, 3.00            # plinth top .. cabinet top
# Dark plinth, slightly larger than the carcass so the cabinet reads as
# load-bearing on it; two front levelling feet for placement stability.
box('Dessert_plinth', (dscx, ds_y, .08), (ds_w+.08, ds_d+.06, .16),
    MAT['steel_dark'], 'glass', .01, 'SIGN_01 kiosk base on sidewalk')
for fx in [dscx-ds_w/2+.12, dscx+ds_w/2-.12]:
    cyl('Dessert_foot_%+.2f' % fx, (fx, ds_y-ds_d/2+.08, .025), .028, .05,
        MAT['steel_dark'], 'glass', evidence='SIGN_01 levelling feet')
# White carcass.
box('Dessert_cabinet_body', (dscx, ds_y, (ds_h0+ds_h1)/2),
    (ds_w, ds_d, ds_h1-ds_h0), MAT['cabinet'], 'glass', .015,
    'SIGN_01 white lightbox cabinet')
# Corner trims cover the carcass joints.
for cx in [dscx-ds_w/2+.03, dscx+ds_w/2-.03]:
    box('Dessert_corner_trim_%+.2f' % cx, (cx, ds_y-ds_d/2+.035, (ds_h0+ds_h1)/2),
        (.06, .07, ds_h1-ds_h0-.04), MAT['cabinet'], 'glass', .008,
        'SIGN_01 corner trim covers panel seams')
# Three stacked lightbox modules: frame rails + recessed glowing screen +
# graphic bands, dark gasket seam between modules.
ds_fy = ds_y - ds_d/2               # front plane of cabinet
for i in range(3):
    mz0 = .26 + i * .89
    mz1 = mz0 + .84
    mcz = (mz0+mz1)/2
    box('Dessert_module_%02d_top_rail' % (i+1), (dscx, ds_fy-.03, mz1-.035),
        (ds_w-.12, .06, .07), MAT['cabinet'], 'glass', .006, 'SIGN_01 frame')
    box('Dessert_module_%02d_bottom_rail' % (i+1), (dscx, ds_fy-.03, mz0+.035),
        (ds_w-.12, .06, .07), MAT['cabinet'], 'glass', .006, 'SIGN_01 frame')
    for mx in [dscx-ds_w/2+.09, dscx+ds_w/2-.09]:
        box('Dessert_module_%02d_side_%+.2f' % (i+1, mx),
            (mx, ds_fy-.03, mcz), (.07, .06, .84), MAT['cabinet'], 'glass',
            .006, 'SIGN_01 frame')
    # Recessed screen sits 3cm behind the frame face.
    box('Dessert_menu_screen_%02d' % (i+1), (dscx, ds_fy+.012, mcz),
        (ds_w-.30, .045, .68), MAT['cyan_lit'], 'glass', .008,
        'SIGN_01;EXT_01 cyan menu glow, screen recessed in frame')
    box('Dessert_screen_highlight_%02d' % (i+1), (dscx, ds_fy-.014, mcz+.16),
        (ds_w-.34, .012, .12), MAT['screen_hi'], 'glass',
        evidence='SIGN_01 bright menu band')
    box('Dessert_screen_thumb_%02d' % (i+1), (dscx-ds_w/2+.32, ds_fy-.014, mcz-.13),
        (.30, .012, .30), MAT['screen_warm'], 'glass',
        evidence='SIGN_01 product photo block')
    if i < 2:
        box('Dessert_gasket_seam_%02d' % (i+1), (dscx, ds_fy-.045, mz1+.025),
            (ds_w-.10, .02, .05), MAT['gasket'], 'glass',
            evidence='SIGN_01 dark seam between modules')
# Shallow top cap with a small overhang sheds water and caps the carcass.
box('Dessert_top_cap', (dscx, ds_y, ds_h1+.025), (ds_w+.06, ds_d+.05, .05),
    MAT['cabinet'], 'glass', .012, 'SIGN_01 top cap')

# Recessed entrance: glazed wall set back, double doors.
rec = S['entrance_recess']
box('Entrance_recess_left_wall', (e0+.1, rec/2, 1.6), (.2, rec, 3.2),
    MAT['podium'], 'glass', .01, 'EXT_01;EXT_02')
box('Entrance_recess_right_wall', (e1-.1, rec/2, 1.6), (.2, rec, 3.2),
    MAT['podium'], 'glass', .01, 'EXT_01;EXT_02')
box('Entrance_recess_soffit', ((e0+e1)/2, rec/2, 3.12), (e1-e0, rec, .16),
    MAT['canopy'], 'canopy', .01, 'EXT_01 recessed soffit')
glazing('Entrance_glazed_wall', e0, e1, y=rec)
dcx = S['door_center_x']
dw = S['door_width']
box('Entrance_door_center_mullion', (dcx, rec-.03, 1.6), (.08, .12, 2.84),
    MAT['frame'], 'glass', .01, 'EXT_01;EXT_02')
box('Entrance_door_head', (dcx, rec-.03, 2.98), (dw, .14, .1),
    MAT['frame'], 'glass', .01, 'EXT_01;EXT_02')
# Warm interior backing seen through entrance glass (abstract, no furniture).
box('Entrance_warm_interior', ((e0+e1)/2, rec+1.1, 1.7),
    (e1-e0-.3, .08, 2.9), MAT['warm'], 'glass',
    evidence='EXT_01 warm glow through entrance glazing;CNT_01;CNT_03;ENV_01 warm interior')
# ---------- entrance door leaves + stainless pull handles (EXT_01) ----------
# Photo: double doors in the recessed glazed wall, each leaf aluminium-framed
# with a stainless kick plate and a horizontal cylindrical pull bar held off
# the glass by two standoffs with round base plates per leaf.
dl_y = rec - .06                    # door plane just in front of the glazing
dl_x0, dl_x1 = dcx - dw/2, dcx + dw/2
for li, (lx0, lx1) in enumerate([(dl_x0, dcx), (dcx, dl_x1)]):
    lw = lx1 - lx0
    lcx = (lx0+lx1)/2
    # Perimeter frame: bottom/top rails and the outer stile (meeting stiles
    # are the existing centre mullion).
    box('Door_leaf_%d_bottom_rail' % li, (lcx, dl_y, .24), (lw, .10, .12),
        MAT['frame'], 'glass', .008, 'EXT_01 door leaf frame')
    box('Door_leaf_%d_top_rail' % li, (lcx, dl_y, 2.92), (lw, .10, .12),
        MAT['frame'], 'glass', .008, 'EXT_01 door leaf frame')
    sx = lx0+.045 if li == 0 else lx1-.045
    box('Door_leaf_%d_outer_stile' % li, (sx, dl_y, 1.58), (.09, .10, 2.80),
        MAT['frame'], 'glass', .008, 'EXT_01 door leaf frame')
    # Stainless kick plate: the worn lower zone of each leaf.
    box('Door_leaf_%d_kick_plate' % li, (lcx, dl_y-.056, .47), (lw-.16, .012, .34),
        MAT['kick'], 'glass', .004, 'EXT_01 worn stainless kick plate')
    # Pull bar: horizontal tube, one per leaf, mounted at handle height.
    bar_z = 1.06
    cyl('Door_leaf_%d_pull_bar' % li, (lcx, dl_y-.15, bar_z), .022, lw-.20,
        MAT['steel'], 'glass', rot=(0, math.pi/2, 0), vertices=32,
        evidence='EXT_01 horizontal stainless pull handle')
    # Standoffs: short horizontal tubes from glass to bar, round base plates.
    for si, sox in enumerate([lcx-lw/4, lcx+lw/4]):
        cyl('Door_leaf_%d_standoff_%d' % (li, si), (sox, dl_y-.075, bar_z),
            .013, .15, MAT['steel'], 'glass', rot=(math.pi/2, 0, 0),
            evidence='EXT_01 handle standoff fixing')
        cyl('Door_leaf_%d_baseplate_%d' % (li, si), (sox, dl_y-.005, bar_z),
            .045, .012, MAT['steel_dark'], 'glass', rot=(math.pi/2, 0, 0),
            vertices=32, evidence='EXT_01 round base plate on glass')
    # Dark end caps close the tube ends.
    for ex in [lcx-(lw-.20)/2, lcx+(lw-.20)/2]:
        cyl('Door_leaf_%d_endcap_%+.2f' % (li, ex), (ex, dl_y-.15, bar_z),
            .024, .012, MAT['steel_dark'], 'glass', rot=(0, math.pi/2, 0),
            evidence='EXT_01 pull bar end cap')

# Right ground-floor glazing (poster zone in photos; kept as plain glass).
glazing('Right_storefront_glass', e1, 7.5)
box('Right_glass_dim_interior', ((e1+7.5)/2, 2.0, 1.7), (7.5-e1-.3, .08, 2.9),
    MAT['warm'], 'glass', evidence='EXT_02 interior hint')

# ---------- white canopy band with warm downlights ----------
cz0, cz1 = S['canopy_z']
box('White_canopy_band', ((sx1+7.5)/2, -.18, (cz0+cz1)/2),
    (7.5-sx1, .9, cz1-cz0), MAT['canopy'], 'canopy', .03, 'EXT_01;EXT_02;EXT_03')
box('Canopy_underside_soffit', ((sx1+7.5)/2, -.18, cz0+.02),
    (7.5-sx1-.06, .86, .05), MAT['canopy'], 'canopy', evidence='EXT_03')
# Recessed round downlights: emissive disk + real spotlight for the night state.
down_x = [-3.0, -.6, 1.8, 4.2, 6.4]
for i, dx0 in enumerate(down_x):
    bpy.ops.mesh.primitive_cylinder_add(radius=.11, depth=.03,
                                        location=(dx0, -.32, cz0-.01))
    disk = bpy.context.object
    disk.name = 'Canopy_downlight_lens_%02d' % (i+1)
    disk.data.materials.append(MAT['down_lit'])
    move_to(disk, 'canopy')
    tag(disk, disk.name, 'EXT_01;EXT_03 warm canopy downlights', True)

# ---------- red lit sign box over the entrance ----------
rz0, rz1 = S['red_sign_z']
rx0, rx1 = S['red_sign_x']
box('Entrance_red_sign_box', ((rx0+rx1)/2, -.10, (rz0+rz1)/2),
    (rx1-rx0, .5, rz1-rz0), MAT['red_lit'], 'sign', .04,
    'EXT_01;EXT_02 red lit sign box')
pts = m_outline((rx0+rx1)/2, rz0+.10, 1.15, .58)
M_red = prism_from_xz('Red_box_golden_M', pts, -.40, -.36, MAT['gold_lit'],
                      'sign', 'EXT_01;EXT_02;EXT_03', False)
bevel(M_red, .012, 2)

# ---------- level 2: full-height glass band + dark wall with hotel sign ----------
g0, g1 = L2['glass_band']
lz0, lz1 = L2['glass_z']
box('Level2_glass_band', ((g0+g1)/2, .05, (lz0+lz1)/2),
    (g1-g0, .07, lz1-lz0), MAT['glass'], 'glass',
    evidence='SEAT_02;SEAT_04 full-height glazing')
for i in range(5):
    mx = g0 + .35 + i * ((g1-g0-.7)/4)
    box('Level2_vertical_mullion_%02d' % (i+1), (mx, .02, (lz0+lz1)/2),
        (.09, .12, lz1-lz0), MAT['frame'], 'glass', .01, 'SEAT_02;SEAT_04')
box('Level2_warm_interior_back', ((g0+g1)/2, 1.4, (lz0+lz1)/2),
    (g1-g0-.4, .10, lz1-lz0-.3), MAT['warm_lit'], 'glass',
    evidence='SEAT_01;SEAT_03 warm lit dining room')
dw0, dw1 = L2['dark_wall']
box('Level2_dark_wall_right', ((dw0+dw1)/2, .10, (lz0+lz1)/2),
    (dw1-dw0, .35, lz1-lz0), MAT['podium'], 'facade', .02,
    'EXT_01 dark hotel wall right of glazing')
text_obj('Lido_hotel_sign', '麗都酒店', 6.45, -.26, 5.7, .46,
         MAT['hotel_lit'], font=FONT_CN, extrude=.03,
         evidence='EXT_01 hotel name right of McDonalds')

# ---------- left wood-slat strip with McCafe script ----------
box('Slat_strip_base', ((sx0+sx1)/2, .06, pt/2),
    (sx1-sx0, .3, pt), MAT['slat_dark'], 'facade', .01,
    'EXT_02;EXT_03 wood-slat cladding')
z = .14
i = 0
while z < pt-.1:
    box('Wood_slat_%02d' % i, ((sx0+sx1)/2, -.10, z+.11),
        (sx1-sx0-.06, .16, .20), MAT['slat'], 'facade', .012,
        'EXT_02;EXT_03 horizontal slats')
    z += .28
    i += 1
text_obj('McCafe_script_on_slats', 'McCafé', (sx0+sx1)/2, -.22, 6.1, .62,
         MAT['white_lit'], font=FONT_ITALIC, extrude=.03,
         evidence='EXT_02;EXT_03 McCafe script on slats')

# ---------- black panel with giant lit golden M ----------
bx0, bx1 = BP['x']
bz0, bz1 = BP['z']
box('Black_M_panel', ((bx0+bx1)/2, -.11, (bz0+bz1)/2),
    (bx1-bx0, BP['depth'], bz1-bz0), MAT['frame'], 'sign', .02,
    'EXT_02;EXT_03 black sign panel')
pts = m_outline(BP['m_center_x'], BP['m_base_z'], BP['m_width'], BP['m_height'])
M_big = prism_from_xz('Golden_arches_M_lit_panel', pts, -.50, -.26,
                      MAT['gold_lit'], 'sign',
                      'EXT_01 night lit M;EXT_02;EXT_03 day M', False)
bevel(M_big, .022, 3)
M_big['landmark'] = '黑色面板上的发光金拱门 M（EXT_01 夜景可见）'

# ---------- McCafe blade sign on the right corner ----------
mbz0, mbz1 = CONFIG['mccafe_blade']['z']
mbx = CONFIG['mccafe_blade']['x']
box('McCafe_blade_sign', (mbx, -.45, (mbz0+mbz1)/2),
    (.16, 1.0, mbz1-mbz0), MAT['frame'], 'sign', .02,
    'EXT_03 right corner McCafe blade sign')
pts = m_outline(mbx, mbz0+.85, .55, .5)
M_blade = prism_from_xz('Blade_sign_M', pts, -.98, -.94, MAT['gold_lit'],
                        'sign', 'EXT_03', False)
text_obj('Blade_sign_McCafe', 'McCafé', mbx-.085, -.60, mbz0+.45, .24,
         MAT['white_lit'], font=FONT_ITALIC, extrude=.012, evidence='EXT_03')
# Small white direction arrow below the wordmark.
box('Blade_sign_arrow_stem', (mbx-.085, -.70, mbz0+.16), (.02, .3, .05),
    MAT['white_lit'], 'sign', evidence='EXT_03 white arrow')

# ---------- entrance threshold (flush with sidewalk, no steps in photos) ----------
box('Entrance_threshold', (dcx, rec/2, .05), (dw+.3, rec+.15, .1),
    MAT['step'], 'steps', .02, 'EXT_01;EXT_02 flush threshold')

# ---------- store lighting (collection 07, travels with the model) ----------
def spot(name, loc, energy, color, size_rad, target, blend=.5):
    data = bpy.data.lights.new(name, 'SPOT')
    data.energy = energy
    data.color = color
    data.spot_size = math.radians(size_rad)
    data.spot_blend = blend
    o = bpy.data.objects.new(name, data)
    COL['light'].objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z', 'Y').to_euler()
    o['light_role'] = 'store_photo_lighting'
    return o

def area_light(name, loc, energy, color, size, target, col='light'):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.color = color
    data.shape = 'DISK'
    data.size = size
    o = bpy.data.objects.new(name, data)
    COL[col].objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z', 'Y').to_euler()
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

def srgb_f(hex_color):
    return srgb(hex_color)

# Warm pools under the canopy (EXT_01 / EXT_03).
for i, dx0 in enumerate(down_x):
    spot('Canopy_downlight_spot_%02d' % (i+1), (dx0, -.32, cz0-.05), 110,
         srgb_f(LC['downlight_warm']), 75, (dx0, -.5, 0))
# Warm interior of ground floor and level 2 (CNT_01..03, SEAT_01..04).
# Wide-cone spots stand in for area lights: KHR_lights_punctual has no area
# type, so anything exported to GLB must be spot/point/directional.
spot('Ground_interior_warm', (1.0, 3.0, 3.2), 450,
     srgb_f(LC['interior_warm_light']), 150, (1.0, -1.0, 1.4), blend=.85)
spot('Level2_interior_warm', (-.2, 3.4, 6.5), 550,
     srgb_f(LC['interior_warm_light']), 150, (-.2, -1.0, 5.4), blend=.85)
# Warm glow that escapes through the entrance glazing (EXT_01 door glow).
point('Entrance_warm_glow', (dcx, rec+.5, 1.8), 150,
      srgb_f(LC['interior_warm_light']))
# Cyan-white glow in front of the dessert-station screens (SIGN_01).
point('Dessert_lightbox_glow', (dscx, ds_fy-.35, 1.7), 85,
      srgb_f(LC['lightbox_cyan']))
# Warm wash that the lit M throws onto its black panel (EXT_01 halo).
spot('M_panel_warm_wash', (BP['m_center_x'], -1.6, 6.6), 150,
     srgb_f(LC['mcd_yellow'] if False else LC['downlight_warm']), 130,
     (BP['m_center_x'], 0, 6.4), blend=.8)

# ---------- reference metadata ----------
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'
scene['model_scope'] = 'Only McDonalds Lido Hotel podium (2 storeys); no tower, no street scene'
scene['dimensional_accuracy'] = 'Photo-estimated proportions; not surveyed'
scene['reference_photos'] = '02_丽都_EXT_01..03;SIGN_01;CNT_01..03;SEAT_01..04;ENV_01'
scene['lighting_basis'] = 'EXT_01 night facade; SIGN_01 lightboxes; CNT_02 McCafe warm wall; SEAT interior'
scene['source_script'] = 'src/build_lido.py'
scene['config'] = 'src/lido_config.json'

# ---------- preview studio (excluded from export) ----------
box('Studio_shadow_ground', (0, 1.5, -.16), (200, 200, .10), MAT['ground'],
    'studio', evidence='preview only')
world = bpy.data.worlds.new('Lido_world')
scene.world = world
world.use_nodes = True
world_bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')

def studio_area(name, loc, power, size, color, target):
    return area_light(name, loc, power, color, size, target, col='studio')

studio_area('Key_large_softbox', (-9, -13, 16), 2100, 8, (1.0, .92, .82), (0, 0, 4))
studio_area('Fill_cool_softbox', (11, -8, 10), 1500, 7, (.8, .88, 1.0), (0, 1, 4))
studio_area('Top_rim_softbox', (1, 9, 16), 2400, 6, (1.0, .96, .88), (0, 2, 5))

def camera(name, loc, target, ortho):
    data = bpy.data.cameras.new(name)
    data.type = 'ORTHO'
    data.ortho_scale = ortho
    o = bpy.data.objects.new(name, data)
    COL['studio'].objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z', 'Y').to_euler()
    return o

CAMS = {
    '01_front_day': camera('CAM_01_front_elevation', (0, -30, 6.6), (0, 1.0, 4.4), 19.5),
    '02_oblique_day': camera('CAM_02_three_quarter', (17, -26, 14), (0, 1.2, 4.2), 22.5),
    '03_night_front': camera('CAM_03_night_front', (0, -30, 6.6), (0, 1.0, 4.4), 19.5),
    '04_night_oblique': camera('CAM_04_night_three_quarter', (-16, -25, 12), (0, 1.2, 4.2), 22.5),
    '05_night_detail': camera('CAM_05_night_entrance_detail', (6, -17, 5.2), (.6, .4, 2.6), 12.5),
    '06_night_door_detail': camera('CAM_06_night_door_handle_closeup',
                                   (3.4, -7.0, 2.1), (1.0, .84, 1.05), 3.6),
}

def set_day():
    world_bg.inputs[0].default_value = (.72, .77, .82, 1)
    world_bg.inputs[1].default_value = .45
    for o in COL['studio'].objects:
        o.hide_render = False
    for o in COL['light'].objects:
        o.hide_render = True

def set_night():
    world_bg.inputs[0].default_value = (*srgb_f(LC['night_world']), 1)
    world_bg.inputs[1].default_value = .06
    for o in COL['studio'].objects:
        if o.type == 'LIGHT':
            o.hide_render = True
    for o in COL['light'].objects:
        o.hide_render = False

scene.render.engine = 'CYCLES'
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

# Opening view: night three-quarter, since lighting is this store's focus.
scene.camera = CAMS['04_night_oblique']

t = bpy.data.texts.new('READ_ME_模型说明')
t.write('麦当劳北京路丽都酒店店｜参数化建筑模型（含真实照片灯光）\n\n'
        '单位：米。尺寸均为照片推定，非实测。\n'
        '范围为丽都大酒店裙楼一、二层；酒店塔楼照片中不可辨，未建模。\n'
        '01-07 集合为建筑与门店灯光；90 为预览灯光/地面，导出不含 90。\n'
        '灯光依据：EXT_01 夜景立面 / SIGN_01 灯箱 / CNT_02 麦咖啡暖光 / SEAT 二层。\n'
        '切换日景：隐藏 07_LIGHTING_STORE、显示 90 灯光；夜景反之。\n'
        '文字在 .blend 中保持可编辑；脚本与 lido_config.json 可复建。\n')
bpy.ops.file.pack_all()
blend_path = os.path.join(MODELS, 'Lido_McDonalds.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

# ---------- exports (text converted to mesh only after saving the .blend) ----------
bpy.ops.object.select_all(action='DESELECT')
for o in list(COL['sign'].objects):
    if o.type in {'FONT', 'CURVE'}:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.convert(target='MESH')
        o.select_set(False)
model_objects = []
for key in ['shell', 'facade', 'canopy', 'glass', 'sign', 'steps']:
    model_objects.extend([o for o in COL[key].objects if o.type in {'MESH', 'CURVE'}])
light_objects = [o for o in COL['light'].objects if o.type == 'LIGHT']
bpy.ops.object.select_all(action='DESELECT')
for o in model_objects + light_objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = model_objects[0]

bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, 'Lido_McDonalds.glb'),
    export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
    export_materials='EXPORT', export_extras=True, export_lights=True)
bpy.ops.wm.obj_export(filepath=os.path.join(MODELS, 'Lido_McDonalds.obj'),
    export_selected_objects=True, apply_modifiers=True,
    export_materials=True, path_mode='COPY')
try:
    bpy.ops.export_scene.fbx(filepath=os.path.join(MODELS, 'Lido_McDonalds.fbx'),
        use_selection=True, use_mesh_modifiers=True, add_leaf_bones=False)
except Exception as e:
    print('FBX export warning:', e)

# ---------- previews: 2 day + 3 night ----------
if '--no-render' not in sys.argv:
    plan = [('01_front_day', 'day'), ('02_oblique_day', 'day'),
            ('03_night_front', 'night'), ('04_night_oblique', 'night'),
            ('05_night_detail', 'night'), ('06_night_door_detail', 'night')]
    for key, mode in plan:
        set_day() if mode == 'day' else set_night()
        scene.camera = CAMS[key]
        scene.render.filepath = os.path.join(PREVIEWS, 'Lido_' + key + '.png')
        bpy.ops.render.render(write_still=True)
    set_day()

# ---------- manifest ----------
mesh_stats = {'vertices': 0, 'polygons': 0,
              'objects': len(model_objects), 'lights': len(light_objects),
              'collections': []}
for o in model_objects:
    if o.type == 'MESH':
        mesh_stats['vertices'] += len(o.data.vertices)
        mesh_stats['polygons'] += len(o.data.polygons)
for key in ['shell', 'facade', 'canopy', 'glass', 'sign', 'steps', 'light']:
    mesh_stats['collections'].append({'name': COL[key].name,
                                      'objects': len(COL[key].objects)})
mesh_stats['dimensions_m'] = {'width': w, 'depth': d, 'height': pt}
mesh_stats['scale_note'] = CONFIG['scale_basis']
mesh_stats['source_photos'] = scene['reference_photos']
mesh_stats['lighting_states'] = ['DAY (studio, preview only)',
                                 'NIGHT (store lights, exported)']
mesh_stats['exports'] = ['Lido_McDonalds.blend', 'Lido_McDonalds.glb',
                         'Lido_McDonalds.obj', 'Lido_McDonalds.fbx']
json.dump(mesh_stats, open(os.path.join(MODELS, 'model_manifest.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=2)
print('BUILD_COMPLETE', json.dumps(mesh_stats, ensure_ascii=False))
