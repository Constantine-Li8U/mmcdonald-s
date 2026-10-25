# -*- coding: utf-8 -*-
"""Parametric L1 photo-estimated model of the former United Kingdom Hotel, now McDonald's Kew.
Run with Blender 4.5: blender --background --python build_united_kingdom_hotel.py
All dimensions are metres and photo-estimated, not surveyed.
"""
import bpy, math, json, os, sys, random
from mathutils import Vector, Euler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, 'src', 'united_kingdom_hotel_config.json'), encoding='utf-8-sig') as f:
    CONFIG = json.load(f)
B = CONFIG['building']; C = CONFIG['materials']
MODELS = os.path.join(ROOT, 'models'); PREVIEWS = os.path.join(ROOT, 'previews')
os.makedirs(MODELS, exist_ok=True); os.makedirs(PREVIEWS, exist_ok=True)
FRONT_Y = 0.0

# ---------- scene and collections ----------
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
# Remove Blender's default empty collection as well as any prior generated collections.
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
def new_collection(name):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); return c
COL = {
    'shell': new_collection('01_HOST_SHELL'),
    'stone': new_collection('02_FACADE_STONE'),
    'arch': new_collection('03_ARCHITECTURAL_ARCHES'),
    'glass': new_collection('04_GLAZING_AND_DOORS'),
    'sign': new_collection('05_SIGNAGE'),
    'steps': new_collection('06_ENTRANCE_STEPS'),
    'lighting': new_collection('07_LIGHTING_STORE'),
    'studio': new_collection('90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT'),
    'ref': new_collection('99_REFERENCE_METADATA'),
}
def move_to(obj, key):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    COL[key].objects.link(obj); return obj
def tag(obj, part, evidence, estimated=True):
    obj['project'] = CONFIG['project']; obj['part'] = part
    obj['visual_evidence'] = evidence; obj['photo_estimated'] = estimated
    return obj

def srgb(h):
    h = h.lstrip('#'); vals = [int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in vals)

def pbr(name, color, rough=.5, metal=0.0, emission=0.0, noise=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    rgba = (*srgb(color),1); bs.inputs['Base Color'].default_value = rgba
    bs.inputs['Roughness'].default_value = rough; bs.inputs['Metallic'].default_value = metal
    if 'Emission Color' in bs.inputs:
        bs.inputs['Emission Color'].default_value = rgba; bs.inputs['Emission Strength'].default_value = emission
    if noise:
        tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=noise; tex.inputs['Detail'].default_value=4.0; tex.inputs['Roughness'].default_value=.7
        bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.22; bump.inputs['Distance'].default_value=.10
        nt.links.new(tex.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface']); m.diffuse_color=rgba; return m
MAT = {
    'brick': pbr('BRICK_warm_red_face', C['brick'], .82, noise=7.0),
    'brick_alt': pbr('BRICK_variation_red_face', C['brick_alt'], .79, noise=8.0),
    'brick_dark': pbr('BRICK_dark_header_band', C['brick_dark'], .84, noise=8.0),
    'mortar': pbr('MORTAR_recessed_brick_joints', C['mortar'], .91),
    'goldstone': pbr('STONE_golden_art_deco_cladding', C['stone_gold'], .48, noise=4.0),
    'goldhi': pbr('STONE_highlight_carved_edges', C['stone_highlight'], .42, noise=3.2),
    'stonejoint': pbr('STONE_joint_shadow', C['stone_joint'], .78),
    'glass': pbr('GLASS_dark_reflective_shopfront', C['glass'], .22, .12),
    'glasswarm': pbr('GLASS_warm_interior_reflection', C['glass_warm'], .30, .06, .22),
    'frame': pbr('METAL_dark_window_frames', C['frame'], .29, .72),
    'metal': pbr('METAL_brushed_balcony_rails', C['metal'], .31, .78),
    'awning': pbr('AWNING_cream_streamline_canopy', C['awning'], .38, .18),
    'awning_edge': pbr('AWNING_dark_edge_trim', C['awning_edge'], .45, .28),
    'gold': pbr('SIGN_McDonalds_golden_yellow', C['mcd_yellow'], .23, .42, .12),
    'redsign': pbr('SIGN_red_drive_thru_face', C['sign_red'], .36, .12, .04),
    'white': pbr('SIGN_warm_white_letters', C['sign_white'], .34, .03, .18),
    'roof': pbr('ROOF_red_brown_tile_membrane', C['roof'], .88, noise=5.0),
    'step': pbr('STEP_grey_concrete', C['step'], .82, noise=2.0),
    'ground': pbr('STUDIO_neutral_ground', C['ground'], .88),
    'light': pbr('LIGHT_warm_under_awning', '#FFBE62', .28, 0.0, 4.0),
}
def bevel(obj, amount=.03, segments=2):
    mod=obj.modifiers.new('Edge_softening','BEVEL'); mod.width=amount; mod.segments=segments; return obj
def box(name, loc, dims, mat, key, bevel_amt=0.0, evidence='photo-derived', estimated=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat: o.data.materials.append(mat)
    if bevel_amt: bevel(o, bevel_amt)
    move_to(o,key); return tag(o,name,evidence,estimated)
def mesh_obj(name, verts, faces, mat, key, evidence='photo-derived', estimated=True):
    me=bpy.data.meshes.new(name+'_mesh'); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); COL[key].objects.link(o)
    if mat: me.materials.append(mat)
    return tag(o,name,evidence,estimated)
def curve_path(name, pts, radius, mat, key, cyclic=False, evidence='photo-derived'):
    cu=bpy.data.curves.new(name+'_curve','CURVE'); cu.dimensions='3D'; cu.resolution_u=2
    cu.bevel_depth=radius; cu.bevel_resolution=3; sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts): p.co=(*co,1)
    sp.use_cyclic_u=cyclic; o=bpy.data.objects.new(name,cu); COL[key].objects.link(o); cu.materials.append(mat)
    return tag(o,name,evidence)
def rounded_rect(w,d,r,z0,z1,y0=0):
    # clockwise plan polygon with front at y0, back at y0+d
    pts=[]; n=12
    centers=[(w/2-r,y0+r,math.pi*1.5,math.pi*2),(w/2-r,y0+d-r,0,math.pi*.5),(-w/2+r,y0+d-r,math.pi*.5,math.pi),(-w/2+r,y0+r,math.pi,math.pi*1.5)]
    pts.append((-w/2+r,y0)); pts.append((w/2-r,y0))
    for cx,cy,a,b in centers[:1]:
        for i in range(n+1):
            t=a+(b-a)*i/n; pts.append((cx+r*math.cos(t),cy+r*math.sin(t)))
    for cx,cy,a,b in centers[1:]:
        for i in range(1,n+1):
            t=a+(b-a)*i/n; pts.append((cx+r*math.cos(t),cy+r*math.sin(t)))
    # close from left front already included by arc
    npts=len(pts); verts=[(x,y,z0) for x,y in pts]+[(x,y,z1) for x,y in pts]
    faces=[tuple(reversed(range(npts))),tuple(range(npts,2*npts))]
    faces += [(i,(i+1)%npts,(i+1)%npts+npts,i+npts) for i in range(npts)]
    return verts,faces

def extrude_plan(name,w,d,r,z0,z1,mat,key,evidence):
    v,f=rounded_rect(w,d,r,z0,z1); return mesh_obj(name,v,f,mat,key,evidence)
def arc_points(cx,cy,r,a0,a1,z,n=32):
    return [(cx+r*math.cos(a0+(a1-a0)*i/n),cy+r*math.sin(a0+(a1-a0)*i/n),z) for i in range(n+1)]
def poly_prism_xz(name, pts, y0,y1,mat,key,evidence='photo-derived',estimated=True):
    n=len(pts); verts=[(x,y0,z) for x,z in pts]+[(x,y1,z) for x,z in pts]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh_obj(name,verts,faces,mat,key,evidence,estimated)
def text_obj(name, body, loc, size, mat, font=None, evidence='photo-signage'):
    cu=bpy.data.curves.new(name+'_editable_text','FONT'); cu.body=body; cu.align_x='CENTER'; cu.align_y='CENTER'; cu.size=size; cu.extrude=.015; cu.bevel_depth=.003; cu.bevel_resolution=2
    if font: cu.font=font
    o=bpy.data.objects.new(name,cu); COL['sign'].objects.link(o); o.location=loc; o.rotation_euler=(math.pi/2,0,0); cu.materials.append(mat); return tag(o,name,evidence,False)
try: FONT=bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')
except: FONT=None
try: FONT_ITALIC=bpy.data.fonts.load('C:/Windows/Fonts/arialbi.ttf')
except: FONT_ITALIC=FONT

# ---------- base masses ----------
main=extrude_plan('Host_rounded_streamline_shell',B['width'],B['depth'],B['corner_radius'],0,B['main_height'],MAT['brick'],'shell','EXT_01_front;EXT_02_oblique;EXT_03_side_detail;EXT_05_wide_context')
bevel(main,.05,2)
# slightly raised rear/side brick volumes create the stepped 1930s silhouette
box('Host_rear_roof_block',(0,11.0,7.65),(19.0,6.8,1.5),MAT['brick_alt'],'shell',.12,'EXT_05_wide_context;inferred completion')
box('Host_left_rear_block',(-9.4,8.4,7.6),(3.7,6.6,1.4),MAT['brick_alt'],'shell',.14,'EXT_03_side_detail;inferred completion')
box('Host_right_rear_block',(9.4,8.4,7.6),(3.7,6.6,1.4),MAT['brick_alt'],'shell',.14,'EXT_02_oblique;inferred completion')
box('Host_flat_roof',(0,7.5,8.55),(25.2,14.2,.24),MAT['roof'],'shell',.08,'EXT_02_oblique;EXT_05_wide_context')
# central tower brick core
box('Host_central_tower_core',(0,2.1,9.8),(5.2,5.0,11.8),MAT['brick_alt'],'shell',.08,'EXT_01_front;EXT_04_tower_detail')
# roof brick courses / bands along front
for z in [0.58,0.98,1.38,1.78,2.18,2.58,2.98,3.38,3.78,4.18,4.58,4.98,5.38,5.78,6.18,6.58,6.98,7.38,7.78]:
    box('Brick_course_front_%02d'%int(z*10), (0,-.025,z),(20.0,.035,.018),MAT['mortar'],'stone',0,'EXT_01_front;EXT_03_side_detail')
    # staggered vertical joints, thin but visible in close-ups
    offset=.0 if int(z*10)%2==0 else .22
    for j in range(-18,19):
        x=j*0.56+offset
        if abs(x)<2.8: continue
        box('Brick_joint_vertical_%02d_%02d'%(int(z*10),j),(x,-.032,z+.18),(.018,.028,.34),MAT['mortar'],'stone',0,'EXT_01_front;DETAIL_01_entrance')
# dark horizontal decorative stripes in lower facade
for z in [1.15,2.55,3.02]: box('Facade_dark_horizontal_band_%02d'%int(z*100),(0,-.08,z),(22.0,.16,.16),MAT['brick_dark'],'stone',.015,'EXT_01_front;EXT_02_oblique')

# ---------- central golden art-deco tower cladding ----------
box('Tower_gold_front_panel',(0,-.60,8.1),(4.55,.18,12.0),MAT['goldstone'],'stone',.04,'EXT_01_front;EXT_04_tower_detail')
box('Tower_gold_side_left',(-2.38,1.7,8.1),(.18,4.6,12.0),MAT['goldstone'],'stone',.03,'EXT_04_tower_detail')
box('Tower_gold_side_right',(2.38,1.7,8.1),(.18,4.6,12.0),MAT['goldstone'],'stone',.03,'EXT_04_tower_detail')
for i,x in enumerate([-2.15,-1.15,0,1.15,2.15]):
    box('Tower_vertical_carved_fin_%02d'%i,(x,-.76,8.2),(.22,.16,11.9),MAT['goldhi'],'stone',.035,'DETAIL_01_entrance;EXT_04_tower_detail')
for z in [4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0]:
    box('Tower_horizontal_stone_joint_%02d'%int(z*10),(0,-.775,z),(4.3,.025,.026),MAT['stonejoint'],'stone',0,'EXT_04_tower_detail')
# tower narrow glazed slots at two levels
for z,h in [(6.05,2.25),(10.55,2.4)]:
    box('Tower_narrow_glass_%02d'%int(z*10),(0,-.87,z),(1.45,.06,h),MAT['glass'],'glass',.015,'EXT_01_front;EXT_04_tower_detail')
    for x in [-.63,0,.63]: box('Tower_window_mullion_%02d_%s'%(int(z*10),str(x)),(x,-.92,z),(.06,.06,h-.08),MAT['frame'],'glass',.008,'EXT_04_tower_detail')
    for zz in [z-h/2+.22,z+h/2-.22]: box('Tower_window_crossbar_%02d_%s'%(int(z*10),str(zz)),(0,-.92,zz),(1.38,.06,.05),MAT['frame'],'glass',.004,'EXT_04_tower_detail')
# side pointed fins
for x in [-2.7,2.7]:
    box('Tower_art_deco_side_pier_%s'%x,(x,-.58,7.0),(.36,.25,7.2),MAT['goldhi'],'stone',.04,'EXT_04_tower_detail')
    poly_prism_xz('Tower_art_deco_pier_cap_%s'%x,[(x-.28,10.4),(x,11.0),(x+.28,10.4),(x+.28,9.95),(x-.28,9.95)],-.76,-.48,MAT['goldhi'],'stone','EXT_04_tower_detail')

# ---------- glazing, doors and window frames ----------
def window_set(label,x,z,w,h,y=-.30, awning=False):
    box(label+'_dark_glazing',(x,y,z),(w,.08,h),MAT['glass'],'glass',.018,'EXT_01_front;DETAIL_01_entrance')
    for dx in [-w/2+.06,w/2-.06]: box(label+'_side_frame_%s'%dx,(x+dx,y-.06,z),(.09,.15,h+.08),MAT['frame'],'glass',.012,'EXT_01_front')
    for zz in [z-h/2+.05,z+h/2-.05]: box(label+'_horizontal_frame_%s'%zz,(x,y-.06,zz),(w,.15,.08),MAT['frame'],'glass',.008,'EXT_01_front')
    box(label+'_warm_interior_back',(x,y+.45,z),(w-.20,.05,h-.18),MAT['glasswarm'],'glass',0,'EXT_01_front;EXT_02_oblique')
    if awning:
        box(label+'_cream_canopy',(x,-.72,z+h/2+.40),(w+1.0,1.35,.18),MAT['awning'],'arch',.09,'EXT_01_front;EXT_02_oblique')
        box(label+'_canopy_edge',(x,-1.40,z+h/2+.29),(w+1.05,.10,.10),MAT['awning_edge'],'arch',.045,'EXT_01_front')
for i,(x,w) in enumerate([(-9.0,2.75),(-5.3,2.45),(5.3,2.45),(9.0,2.75)],1): window_set('Ground_storefront_%02d'%i,x,1.95,w,2.15,awning=True)
for i,(x,w) in enumerate([(-9.0,2.55),(-5.2,2.25),(5.2,2.25),(9.0,2.55)],1): window_set('Upper_window_%02d'%i,x,5.75,w,1.75,awning=False)
# curved end windows / side doors, placed on visible side planes
for side in [-1,1]:
    x=side*11.7
    for j,y in enumerate([2.0,5.0,8.0]):
        box('Side_window_%s_%02d_glass'%('L' if side<0 else 'R',j),(x,y,1.95),(.06,1.85,2.0),MAT['glass'],'glass',.018,'EXT_02_oblique;EXT_03_side_detail')
        box('Side_window_%s_%02d_frame'%('L' if side<0 else 'R',j),(x+side*.08,y,1.95),(.12,2.0,2.18),MAT['frame'],'glass',.012,'EXT_03_side_detail')
# central entrance and doors
box('Entrance_recess',(0,-.66,1.55),(2.55,.20,3.2),MAT['brick_dark'],'glass',.02,'DETAIL_01_entrance')
box('Entrance_glazed_double_door',(0,-.79,1.50),(2.18,.08,2.52),MAT['glass'],'glass',.02,'DETAIL_01_entrance;EXT_01_front')
for x in [-1.05,1.05]: box('Entrance_door_jamb_%s'%x,(x,-.85,1.52),(.09,.18,2.62),MAT['frame'],'glass',.01,'DETAIL_01_entrance')
box('Entrance_center_mullion',(0,-.86,1.52),(.07,.18,2.52),MAT['frame'],'glass',.008,'DETAIL_01_entrance')
for x in [-.28,.28]:
    curve_path('Entrance_vertical_pull_handle_%s'%x,[(x,-.93,1.18),(x,-.93,1.95)],.026,MAT['metal'],'glass',evidence='DETAIL_01_entrance')
    for z in [1.22,1.91]: curve_path('Entrance_handle_standoff_%s_%s'%(x,z),[(x,-.93,z),(x,-.80,z)],.016,MAT['metal'],'glass',evidence='DETAIL_01_entrance')
# central tower door canopy / projecting stone balcony
box('Entrance_canopy_slab',(0,-1.16,3.45),(4.9,1.55,.26),MAT['goldhi'],'arch',.12,'DETAIL_01_entrance')
curve_path('Entrance_canopy_front_edge',[(-2.25,-1.92,3.32),(0,-2.03,3.20),(2.25,-1.92,3.32)],.10,MAT['stonejoint'],'arch',evidence='DETAIL_01_entrance')

# ---------- rounded balcony and streamline railings ----------
# front curved balcony slab with cream fascia
box('Balcony_front_slab',(0,-.82,4.35),(21.8,1.45,.20),MAT['awning'],'arch',.10,'EXT_01_front;EXT_02_oblique')
curve_path('Balcony_front_fascia',[(-10.5,-1.55,4.30),(0,-1.60,4.28),(10.5,-1.55,4.30)],.075,MAT['awning_edge'],'arch',evidence='EXT_01_front;EXT_02_oblique')
for z in [4.62,4.86,5.10]: curve_path('Balcony_rail_horizontal_%s'%z,[(-10.3,-1.55,z),(0,-1.62,z),(10.3,-1.55,z)],.028,MAT['metal'],'arch',evidence='EXT_01_front;EXT_02_oblique')
for i in range(25):
    x=-10.1+i*.84; curve_path('Balcony_rail_post_%02d'%i,[(x,-1.55,4.32),(x,-1.55,5.15)],.024,MAT['metal'],'arch',evidence='EXT_01_front')
# side railings follow rounded corners with arcs
for side in [-1,1]:
    cx=side*9.1; cy=2.2
    pts=arc_points(cx,cy,3.1,math.pi if side<0 else 0,math.pi*1.5 if side<0 else math.pi*.5,4.9,28)
    for idx,z in enumerate([4.60,4.86,5.12]): curve_path('Side_balcony_rail_%s_%02d'%('L' if side<0 else 'R',idx),[(x,y,z) for x,y,_ in pts],.026,MAT['metal'],'arch',evidence='EXT_02_oblique;EXT_03_side_detail')
    for idx,(x,y,_) in enumerate(pts[::4]): curve_path('Side_balcony_post_%s_%02d'%('L' if side<0 else 'R',idx),[(x,y,4.34),(x,y,5.15)],.023,MAT['metal'],'arch',evidence='EXT_03_side_detail')

# ---------- upper continuous curved awnings / roofline ----------
# long front canopy plus rounded end caps
box('Upper_streamline_canopy_front',(0,-.78,7.85),(22.2,1.60,.25),MAT['awning'],'arch',.12,'EXT_01_front;EXT_02_oblique')
curve_path('Upper_canopy_front_edge',[(-10.9,-1.58,7.72),(0,-1.68,7.70),(10.9,-1.58,7.72)],.10,MAT['awning_edge'],'arch',evidence='EXT_01_front')
for side in [-1,1]:
    cx=side*9.0; cy=2.0
    pts=arc_points(cx,cy,3.0,math.pi if side<0 else 0,math.pi*1.5 if side<0 else math.pi*.5,7.85,30)
    curve_path('Rounded_end_canopy_edge_%s'%('L' if side<0 else 'R'),pts,.12,MAT['awning_edge'],'arch',evidence='EXT_02_oblique;EXT_03_side_detail')
# roofline vertical parapets and brick rounded caps
for side in [-1,1]:
    box('Roofline_end_pier_%s'%side,(side*11.2,5.2,8.9),(1.2,2.0,2.6),MAT['brick_alt'],'shell',.12,'EXT_02_oblique;EXT_03_side_detail')

# ---------- brand signage ----------
def golden_arches(name,x,y,z,width=2.6,height=2.9,mat=None,key='sign',evidence='photo-signage'):
    """Two dimensional rounded arch strokes, closer to the photographed M signs."""
    mat = mat or MAT['gold']
    # Each arch is a shallow inverted-U with a short straight leg.
    for side in ['L', 'R']:
        pts=[]; n=20
        arch_width = width*.42
        x0 = x - width*.48 if side == 'L' else x + width*.06
        x1 = x0 + arch_width
        cx = (x0+x1)/2
        # leg, shallow elliptical crown, leg; keep a narrow centre gap
        pts.append((x0, y, z))
        pts.append((x0, y, z+height*.28))
        for i in range(n+1):
            t=math.pi - math.pi*i/n
            pts.append((cx + arch_width*.5*math.cos(t), y, z+height*.28 + height*.72*math.sin(t)))
        pts.append((x1, y, z+height*.28))
        pts.append((x1, y, z))
        curve_path('%s_%s'%(name,side),pts,.105,mat,key,evidence=evidence)
golden_arches('Golden_arches_M_ground',0,-1.12,5.00,2.55,2.55,MAT['gold'],'sign','EXT_01_front;SIGN_01')
golden_arches('Golden_arches_M_tower',0,-1.15,8.35,1.55,1.75,MAT['gold'],'sign','EXT_01_front;EXT_04_tower_detail')
# red freestanding drive-thru board and top circular sign
box('Drive_thru_sign_board',(0,-.55,15.55),(5.6,.32,1.48),MAT['redsign'],'sign',.08,'EXT_01_front;EXT_02_oblique;SIGN_02')
text_obj('Drive_thru_sign_title',"McDonald's",(0,-.75,15.77),.72,MAT['white'],FONT,'EXT_01_front;SIGN_02')
text_obj('Drive_thru_sign_subtitle','DRIVE THRU',(0,-.75,15.28),.38,MAT['white'],FONT,'EXT_01_front;SIGN_02')
box('Drive_thru_sign_pole',(0,-.55,14.55),(.18,.18,1.9),MAT['metal'],'sign',.02,'EXT_02_oblique;SIGN_02')
# round M panel atop sign, cylinder axis toward front
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=.88, depth=.20, location=(0,-.73,16.82), rotation=(math.pi/2,0,0)); o=bpy.context.object; o.name='Drive_thru_round_red_panel'; o.data.materials.append(MAT['redsign']); move_to(o,'sign'); tag(o,o.name,'EXT_01_front;SIGN_02')
golden_arches('Golden_arches_M_roof_sign',0,-.88,16.05,1.20,1.35,MAT['gold'],'sign','EXT_01_front;SIGN_02')
text_obj('McCafe_side_wordmark','McCafe',(-10.4,-.90,3.25),.48,MAT['white'],FONT_ITALIC,'EXT_03_side_detail')
text_obj('McDonalds_upper_channel',"McDonald's",(0,-.82,7.28),.62,MAT['white'],FONT,'EXT_01_front')

# ---------- entrance steps ----------
for i in range(3):
    z=.07+i*.12; y=-1.75-i*.36
    box('Entrance_step_%02d'%(i+1),(0,y,z),(3.5+i*.22,.85+i*.38,.14+i*.04),MAT['step'],'steps',.035,'DETAIL_01_entrance;EXT_01_front')
# low plinth around central tower
box('Tower_base_plinth',(0,-.40,.18),(5.4,1.0,.36),MAT['goldhi'],'steps',.06,'DETAIL_01_entrance')

# ---------- store lighting ----------
def point_light(name,loc,energy,color=(1.0,.60,.24),radius=.24):
    d=bpy.data.lights.new(name,'POINT'); d.energy=energy; d.color=color; d.shadow_soft_size=radius
    o=bpy.data.objects.new(name,d); COL['lighting'].objects.link(o); o.location=loc; tag(o,name,'EXT_01_front;EXT_02_oblique',False); return o
for i,x in enumerate([-9,-6,-3,3,6,9]):
    point_light('Store_under_awning_point_%02d'%i,(x,-1.1,7.45),120,(1.0,.63,.30),.18)
    point_light('Store_balcony_warm_point_%02d'%i,(x,-1.28,4.05),75,(1.0,.55,.25),.16)
# emissive slim strips under canopy
for x in [-8.5,-4.3,4.3,8.5]: box('Store_warm_linear_light_%s'%x,(x,-1.18,7.55),(2.4,.06,.04),MAT['light'],'lighting',.01,'EXT_01_front;EXT_02_oblique',False)

# ---------- metadata / studio ----------
scene=bpy.context.scene; scene.unit_settings.system='METRIC'; scene.unit_settings.length_unit='METERS'
scene['model_scope']='Former United Kingdom Hotel facade and host building adapted as McDonalds Kew; no surrounding scene'
scene['dimensional_accuracy']='L1 photo-estimated; not surveyed; not for construction'
scene['store_name']=CONFIG['store_name']; scene['city']=CONFIG['city']; scene['address']=CONFIG['address']
scene['construction_history']='1937-1938; formerly United Kingdom Hotel; architect James Hastie Wardrop'
scene['style']='Australian Streamline Moderne / late Art Deco'
# reference metadata empties
for idx,(name,desc) in enumerate([
    ('REF_EXT_01_front','Front elevation: brick, rounded wings, tower, canopy and signage'),
    ('REF_EXT_02_oblique','Three-quarter elevation: curved balcony, canopy and side windows'),
    ('REF_DETAIL_01_entrance','Central entrance, gold cladding, handles and steps'),
    ('REF_EXT_03_side_detail','Side elevation and McCafe sign'),
    ('REF_EXT_04_tower_detail','Art-deco stone tower, fins and narrow windows'),
    ('REF_EXT_05_wide_context','Wide context used only for overall massing; surroundings excluded'),
]):
    o=bpy.data.objects.new(name,None); COL['ref'].objects.link(o); o.empty_display_type='PLAIN_AXES'; o.hide_render=True; o['description']=desc; o['source']='supplied user photograph'; o['accuracy']='photo-derived'
# preview studio
box('Studio_ground',(0,5,-.16),(120,120,.12),MAT['ground'],'studio',.02,'preview only',False)
world=bpy.data.worlds.new('Neutral_architectural_world'); scene.world=world; world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.09,.11,.13,1); bg.inputs[1].default_value=.28
def area(name,loc,power,size,color,target):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size; d.color=color
    o=bpy.data.objects.new(name,d); COL['studio'].objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
area('Studio_key_softbox',(-14,-18,20),1800,10,(1.0,.84,.68),(0,0,5))
area('Studio_fill_softbox',(14,-10,12),1500,9,(.68,.82,1.0),(0,2,5))
area('Studio_rim_softbox',(0,12,19),2200,8,(1.0,.93,.80),(0,3,7))
def camera(name,loc,target,ortho):
    d=bpy.data.cameras.new(name); d.type='ORTHO'; d.ortho_scale=ortho; d.lens=50
    o=bpy.data.objects.new(name,d); COL['studio'].objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
CAMS={
    '01_front':camera('CAM_01_front_elevation',(0,-35,8.0),(0,1.0,7.1),22.5),
    '02_oblique':camera('CAM_02_three_quarter',(20,-30,16),(0,1.5,7.0),26.5),
    '03_detail':camera('CAM_03_entrance_detail',(9,-20,7.2),(0,-.35,3.9),13.5),
    '04_night':camera('CAM_04_night_three_quarter',(-19,-27,13),(0,1.0,6.4),25.0),
}
scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.resolution_x=CONFIG['render']['resolution_x']; scene.render.resolution_y=CONFIG['render']['resolution_y']; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False; scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.render.image_settings.color_mode='RGBA'
scene.render.engine='BLENDER_EEVEE_NEXT'
# in-file README
readme=bpy.data.texts.new('READ_ME_MODEL_GUIDE'); readme.write('United Kingdom Hotel - McDonalds Kew\n\nUnit: metres. Accuracy: L1 photo-estimated, not surveyed.\nCollections 01-07 are model deliverables; 90 is preview studio and excluded from exports; 99 stores reference metadata.\nAdjust src/united_kingdom_hotel_config.json and rerun build_united_kingdom_hotel.py.\nVisual basis: supplied front, oblique, entrance, side and tower photographs.\nNo people, vehicles, roads, trees or unsupported environmental props.\n')
# save editable blend before export conversion
scene.camera=CAMS['02_oblique']; bpy.ops.wm.save_as_mainfile(filepath=os.path.join(MODELS,'United_Kingdom_Hotel_McDonalds.blend'))

# ---------- exports: 01-07 only; exclude preview studio ----------
export_objs=[]
for key in ['shell','stone','arch','glass','sign','steps','lighting']:
    export_objs.extend([o for o in COL[key].objects if o.type in {'MESH','CURVE','FONT','LIGHT'}])
bpy.ops.object.select_all(action='DESELECT')
for o in export_objs: o.select_set(True)
if export_objs: bpy.context.view_layer.objects.active=export_objs[0]
# convert fonts/curves to meshes for stable interchange; preserve editable text in .blend
for o in list(export_objs):
    if o.type in {'FONT','CURVE'}:
        o.select_set(True); bpy.context.view_layer.objects.active=o
        try: bpy.ops.object.convert(target='MESH')
        except: pass
        o.select_set(False)
export_objs=[o for o in export_objs if o and o.name in bpy.data.objects]
bpy.ops.object.select_all(action='DESELECT')
for o in export_objs: o.select_set(True)
if export_objs: bpy.context.view_layer.objects.active=export_objs[0]
bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS,'United_Kingdom_Hotel_McDonalds.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_extras=True)
mesh_objs=[o for o in export_objs if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in mesh_objs: o.select_set(True)
if mesh_objs:
    bpy.context.view_layer.objects.active=mesh_objs[0]
    bpy.ops.wm.obj_export(filepath=os.path.join(MODELS,'United_Kingdom_Hotel_McDonalds.obj'),export_selected_objects=True,apply_modifiers=True,export_materials=True,path_mode='COPY')
try:
    bpy.ops.export_scene.fbx(filepath=os.path.join(MODELS,'United_Kingdom_Hotel_McDonalds.fbx'),use_selection=True,use_mesh_modifiers=True,add_leaf_bones=False)
except Exception as e: print('FBX export warning:',e)

# restore editable text objects for render if they were converted; rendering uses visible mesh copies fine.
# render fixed views
for key,cam in CAMS.items():
    scene.camera=cam
    if key=='04_night':
        bg.inputs[0].default_value=(.008,.012,.02,1); bg.inputs[1].default_value=.07
        scene.view_settings.look='AgX - Medium High Contrast'
    else:
        bg.inputs[0].default_value=(.09,.11,.13,1); bg.inputs[1].default_value=.28
    scene.render.filepath=os.path.join(PREVIEWS,'United_Kingdom_Hotel_'+key+'.png')
    bpy.ops.render.render(write_still=True)
# manifest
stats={'project':CONFIG['project'],'store_name':CONFIG['store_name'],'city':CONFIG['city'],'address':CONFIG['address'],'accuracy_level':'L1','units':'metres','dimensions_m':{'width':B['width'],'depth':B['depth'],'main_height':B['main_height'],'tower_height':B['tower_height'],'overall_height_including_sign':17.7,'frontage_to_depth_ratio':round(B['width']/B['depth'],3)},'collections':{},'exports':['United_Kingdom_Hotel_McDonalds.blend','United_Kingdom_Hotel_McDonalds.glb','United_Kingdom_Hotel_McDonalds.obj','United_Kingdom_Hotel_McDonalds.mtl','United_Kingdom_Hotel_McDonalds.fbx'],'export_excluded_collection':'90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT','notes':CONFIG['notes'],'source_photos':['EXT_01_front.jpg','EXT_02_oblique.jpg','DETAIL_01_entrance.jpg','EXT_03_side_detail.jpg','EXT_04_tower_detail.jpg','EXT_05_wide_context.jpg']}
for key,c in COL.items(): stats['collections'][c.name]={'objects':len(c.objects),'exported':key not in {'studio','ref'}}
with open(os.path.join(MODELS,'model_manifest.json'),'w',encoding='utf-8') as f: json.dump(stats,f,ensure_ascii=False,indent=2)
print('BUILD_COMPLETE',json.dumps(stats,ensure_ascii=False))
