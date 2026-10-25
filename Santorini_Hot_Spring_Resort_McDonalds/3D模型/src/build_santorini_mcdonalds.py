# -*- coding: utf-8 -*-
"""Parametric photo-estimated model of McDonald's Santorini Hot Spring Resort, Guangzhou.
Blender 4.5.3; metres; L1 visual estimate, not surveyed or for construction.
"""
import bpy, math, json, os
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT,'src','santorini_config.json'),encoding='utf-8-sig') as f: CFG=json.load(f)
B=CFG['building']; C=CFG['materials']; MODELS=os.path.join(ROOT,'models'); PREV=os.path.join(ROOT,'previews')
os.makedirs(MODELS,exist_ok=True); os.makedirs(PREV,exist_ok=True)
# scene reset and deliverable collections
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
def coll(n): c=bpy.data.collections.new(n); bpy.context.scene.collection.children.link(c); return c
COL={k:coll(n) for k,n in [('shell','01_HOST_SHELL'),('stone','02_FACADE_STONE'),('arch','03_ARCHITECTURAL_ARCHES'),('glass','04_GLAZING_AND_DOORS'),('sign','05_SIGNAGE'),('steps','06_ENTRANCE_STEPS'),('lighting','07_LIGHTING_STORE'),('studio','90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT'),('ref','99_REFERENCE_METADATA')]}
def move(o,k):
    for c in list(o.users_collection): c.objects.unlink(o)
    COL[k].objects.link(o)
def tag(o,part,evidence='photo-derived',estimated=True): o['project']=CFG['project']; o['part']=part; o['visual_evidence']=evidence; o['photo_estimated']=estimated; return o
def srgb(h):
    v=[int(h.lstrip('#')[i:i+2],16)/255 for i in (0,2,4)]; return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in v)
def mat(name,color,rough=.5,metal=0.0,emit=0.0,noise=0):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; bs=nt.nodes.get('Principled BSDF') or nt.nodes.new('ShaderNodeBsdfPrincipled'); out=nt.nodes.get('Material Output') or nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(bs.outputs.get('BSDF'),out.inputs.get('Surface')); rgba=(*srgb(color),1); bs.inputs['Base Color'].default_value=rgba; bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    if 'Emission Color' in bs.inputs: bs.inputs['Emission Color'].default_value=rgba; bs.inputs['Emission Strength'].default_value=emit
    if noise:
        tex=nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=noise; tex.inputs['Detail'].default_value=4; tex.inputs['Roughness'].default_value=.75; bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.12; bump.inputs['Distance'].default_value=.05; nt.links.new(tex.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    m.diffuse_color=rgba; return m
M={'stucco':mat('MAT_STUCCO_white_limewash',C['stucco'],.8,noise=3),'stucco_shadow':mat('MAT_STUCCO_shadow_recess',C['stucco_shadow'],.82,noise=3),'cyan':mat('MAT_CYAN_turquoise_trim',C['cyan_trim'],.36,noise=3),'cyan_dark':mat('MAT_CYAN_dark_recess',C['cyan_dark'],.42),'glass':mat('MAT_GLASS_blue_reflective',C['glass'],.18,.18),'glass_warm':mat('MAT_GLASS_warm_interior',C['glass_warm'],.32,.04,.12),'frame':mat('MAT_FRAME_cream_metal',C['frame'],.32,.35),'gold':mat('MAT_SIGN_golden_arches',C['gold'],.24,.35,.06),'gold_dark':mat('MAT_GOLD_dark_edges',C['gold_dark'],.38,.24),'bronze':mat('MAT_STATUE_bronze',C['bronze'],.38,.65),'wood':mat('MAT_WOOD_door',C['wood'],.56,noise=5),'stone':mat('MAT_STONE_steps',C['stone'],.8,noise=3),'white':mat('MAT_SIGN_letters',C['sign_white'],.32,.05,.14),'black':mat('MAT_BLACK',C['black'],.34,.1),'ground':mat('MAT_GROUND',C['ground'],.86,noise=2),'light':mat('MAT_WARM_LIGHT','#FFB34A',.24,0,5)}
def bevel(o,a=.04,s=2): mod=o.modifiers.new('Soft_edge','BEVEL'); mod.width=a; mod.segments=s; return o
def box(n,loc,dims,ma,key='shell',bev=0.0,e='photo-derived'):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=n; o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma); move(o,key); tag(o,n,e); bevel(o,bev) if bev else None; return o
def cyl(n,loc,r,depth,ma,key='arch',verts=48,rot=(0,0,0),e='photo-derived'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rot); o=bpy.context.object; o.name=n; o.data.materials.append(ma); move(o,key); tag(o,n,e); bevel(o,.02,2); return o
def sphere(n,loc,r,ma,key='arch',e='photo-derived'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=r, location=loc); o=bpy.context.object; o.name=n; o.data.materials.append(ma); move(o,key); tag(o,n,e); return o
def curve(n,pts,r,ma,key='arch',cyclic=False,e='photo-derived'):
    cu=bpy.data.curves.new(n+'_curve','CURVE'); cu.dimensions='3D'; cu.resolution_u=3; cu.bevel_depth=r; cu.bevel_resolution=4; sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts): p.co=(*co,1)
    sp.use_cyclic_u=cyclic; o=bpy.data.objects.new(n,cu); COL[key].objects.link(o); cu.materials.append(ma); return tag(o,n,e)
def arch_pts(cx,cy,z0,w,h,n=32):
    # front-facing inverted U: vertical legs then semicircular crown
    r=w/2; zc=z0+h-r; pts=[(cx-r,cy,z0),(cx-r,cy,zc)]
    for i in range(n+1):
        t=math.pi-math.pi*i/n; pts.append((cx+r*math.cos(t),cy,zc+r*math.sin(t)))
    pts.extend([(cx+r,cy,zc),(cx+r,cy,z0)]); return pts
def arch_ring(n,cx,z0,w,h,trim,back=None,front=-.25,key='arch',depth=.08):
    if back: box(n+'_recess',(cx,front+.04,z0+h*.5),(w-.32,depth,h-.1),back,'glass',.025)
    curve(n+'_outline',arch_pts(cx,front,z0,w,h),.16,trim,key)
    # base sill
    box(n+'_sill',(cx,front-.02,z0),(w+.20,.18,.14),trim,key,.02)
def text(n,body,loc,size,ma,font=None,key='sign'):
    cu=bpy.data.curves.new(n+'_editable_text','FONT'); cu.body=body; cu.align_x='CENTER'; cu.align_y='CENTER'; cu.size=size; cu.extrude=.035; cu.bevel_depth=.006; cu.bevel_resolution=3
    if font: cu.font=font
    o=bpy.data.objects.new(n,cu); COL[key].objects.link(o); o.location=loc; o.rotation_euler=(math.pi/2,0,0); cu.materials.append(ma); return tag(o,n,'photo-signage',False)
try: FONT=bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')
except: FONT=None
try: FONTIT=bpy.data.fonts.load('C:/Windows/Fonts/arialbi.ttf')
except: FONTIT=FONT
# host building: broad white resort block and stepped roofline
box('Host_main_white_shell',(0,8.0,4.5),(B['width'],B['depth'],9.0),M['stucco'],'shell',.22,'EXT_01_front;EXT_02_wide;EXT_03_side')
box('Host_left_rear_wing',(-12.4,10.3,5.6),(9.2,13.0,11.2),M['stucco'],'shell',.28,'EXT_03_side;EXT_04_side')
box('Host_right_rear_wing',(12.4,10.3,5.6),(9.2,13.0,11.2),M['stucco'],'shell',.28,'EXT_05_side')
# stepped parapets
for side in [-1,1]:
    for i,(x,z,h) in enumerate([(side*14,9.8,1.6),(side*10.8,10.1,2.2)]): box(f'Parapet_{side}_{i}',(x,1.3,z),(2.9,2.6,h),M['stucco'],'shell',.16,'EXT_03_side')
# central tower mass above front bay
box('Central_tower_core',(0,2.2,12.7),(12.2,5.0,8.0),M['stucco'],'shell',.18,'EXT_01_front;EXT_02_front')
box('Central_tower_top',(0,2.2,16.5),(8.4,4.7,4.8),M['stucco'],'shell',.18,'EXT_01_front')
# front horizontal cornice bands
for z,w,d in [(8.95,31.0,.48),(9.35,29.2,.35),(12.05,13.2,.4),(15.65,10.0,.36)]: box(f'Cornice_{z}',(0,-.30,z),(w,d,.18),M['stucco_shadow'],'stone',.035,'EXT_01_front')
# tall side wing windows, repeated blue arched bays
for side in [-1,1]:
    xs=[-15.2,-11.2,-7.2] if side<0 else [7.2,11.2,15.2]
    for i,x in enumerate(xs):
        # front-facing tall arches, with lower and upper divisions
        arch_ring(f'Front_arch_window_{side}_{i}',x,.75,3.0,6.5,M['cyan'],M['glass'],front=-.53,key='glass')
        box(f'Window_warm_back_{side}_{i}',(x,-.58,3.5),(2.4,.06,5.6),M['glass_warm'],'glass',.01,'EXT_03_side')
        # vertical and horizontal mullions
        box(f'Window_center_mullion_{side}_{i}',(x,-.68,3.4),(.08,.12,5.8),M['frame'],'glass',.01,'EXT_03_side')
        for z in [2.0,4.0,5.9]: box(f'Window_crossbar_{side}_{i}_{z}',(x,-.69,z),(2.55,.12,.07),M['frame'],'glass',.008,'EXT_03_side')
# return side windows on both long sides
for side in [-1,1]:
    x=side*17.1
    for j,y in enumerate([3.0,7.0,11.0,15.0]):
        # side wall arched panel, plane along X
        box(f'Side_glass_{side}_{j}',(x,y,3.4),(.08,2.8,5.8),M['glass'],'glass',.02,'EXT_03_side;EXT_04_side')
        # cyan arch approximation using curve in X constant
        pts=[]; r=1.4; zc=5.2; z0=.75; pts=[(x, y-r,z0),(x,y-r,zc)]
        for i in range(25):
            t=math.pi-math.pi*i/24; pts.append((x,y+r*math.cos(t),zc+r*math.sin(t)))
        pts.append((x,y+r,z0)); curve(f'Side_arch_trim_{side}_{j}',pts,.12,M['cyan'],'arch',e='photo side')
# glass elevator tower on left-front from photos
box('Glass_elevator_volume',(-17.5,3.0,5.7),(4.1,4.5,11.4),M['glass'],'glass',.12,'EXT_01_oblique;EXT_02_wide')
for x in [-19.2,-17.5,-15.8]: box(f'Elevator_vertical_mullion_{x}',(x,.66,5.7),(.08,.14,11.0),M['frame'],'glass',.01,'EXT_01_oblique')
for z in [1.0,3.8,6.6,9.4]: box(f'Elevator_horizontal_mullion_{z}',(-17.5,.62,z),(3.8,.14,.08),M['frame'],'glass',.01,'EXT_01_oblique')
# tower arches and bell opening
for cx,z0,w,h in [(-4.1,10.0,5.7,5.0),(4.1,10.0,5.7,5.0),(0,14.0,4.7,4.0)]: arch_ring(f'Tower_arch_{cx}',cx,z0,w,h,M['stucco'],M['cyan_dark'],front=-.53,key='arch')
# white arch rings over dark openings (second outline)
for cx,z0,w,h in [(-4.1,10.0,5.7,5.0),(4.1,10.0,5.7,5.0),(0,14.0,4.7,4.0)]: curve(f'Tower_white_arch_{cx}',arch_pts(cx,-.72,z0,w,h),.22,M['stucco'],'arch')
# side decorative fins and top battlements
for x in [-7.0,7.0]:
    box(f'Tower_side_pier_{x}',(x,-.4,11.9),(1.2,.8,5.0),M['stucco'],'stone',.08,'EXT_01_front')
    box(f'Tower_side_fin_{x}',(x,-.5,14.8),(.34,.45,3.3),M['stucco'],'stone',.05,'EXT_01_front')
# bell and support
cyl('Bell_body',(0,-.83,15.9),.62,1.15,M['bronze'],'arch',64,rot=(math.pi/2,0,0),e='EXT_01_front')
cyl('Bell_bottom',(0,-.83,15.36),.78,.10,M['gold_dark'],'arch',64,rot=(math.pi/2,0,0),e='EXT_01_front')
cyl('Bell_support',(0,-.83,16.75),.055,1.3,M['bronze'],'arch',32,rot=(math.pi/2,0,0),e='EXT_01_front')
# simple classical statues in lower tower niches
for x in [-4.1,4.1]:
    cyl(f'Statue_{x}_body',(x,-.87,11.45),.25,1.2,M['bronze'],'arch',24,e='EXT_01_front'); sphere(f'Statue_{x}_head',(x,-.87,12.2),.18,M['bronze'],'arch','EXT_01_front'); cyl(f'Statue_{x}_spear',(x+.38,-.87,12.15),.035,1.8,M['bronze'],'arch',16,e='EXT_01_front')
# McDonald's entrance portal, pediment, doors
box('Entrance_recess',(0,-.74,2.15),(6.8,.30,4.1),M['stucco_shadow'],'glass',.06,'EXT_01_front;EXT_02_front')
box('Entrance_glazing',(0,-.94,2.15),(5.55,.10,3.35),M['glass_warm'],'glass',.025,'EXT_01_front')
for x in [-2.75,-1.38,0,1.38,2.75]: box(f'Entrance_mullion_{x}',(x,-1.02,2.15),(.075,.14,3.25),M['frame'],'glass',.01,'DETAIL_entrance')
box('Entrance_header',(0,-1.02,4.04),(7.6,.55,.38),M['stucco'],'stone',.10,'DETAIL_entrance')
# four white classical columns with capitals
for x in [-3.0,3.0]:
    cyl(f'Entrance_column_{x}',(x,-1.18,2.1),.27,3.8,M['stucco'],'stone',32,rot=(0,0,0),e='DETAIL_entrance'); cyl(f'Entrance_cap_{x}',(x,-1.18,4.1),.46,.24,M['stucco_shadow'],'stone',32,e='DETAIL_entrance'); cyl(f'Entrance_base_{x}',(x,-1.18,.25),.42,.18,M['stucco_shadow'],'stone',32,e='DETAIL_entrance')
# central M and wordmark

def m_arches(name,x,y,z,w=3.2,h=3.0,ma=M['gold']):
    for s in [-1,1]:
        x0=x+(s*0.02-.48)*w; x1=x+(s*0.02+.00)*w if s<0 else x+(s*0.48+.48)*w
        # simpler two U loops with central gap
        if s<0: x0=x-w*.46; x1=x-w*.03
        else: x0=x+w*.03; x1=x+w*.46
        r=(x1-x0)/2; zc=z+h*.42; pts=[(x0,y,z),(x0,y,zc)]
        for i in range(25):
            t=math.pi-math.pi*i/24; pts.append(((x0+x1)/2+r*math.cos(t),y,zc+r*math.sin(t)))
        pts.extend([(x1,y,zc),(x1,y,z)]); curve(f'{name}_{s}',pts,.14,ma,'sign',e='photo-signage')
m_arches('McDonalds_Golden_Arches_entrance',0,-1.23,5.15,4.8,3.0)
m_arches('McDonalds_Golden_Arches_side',13.5,-.58,7.1,2.7,2.2)
text('McDonalds_wordmark',"McDonald's",(0,-1.28,4.55),1.05,M['white'],FONT)
text('McCafe_wordmark','McCafe',(-1.9,-1.31,2.0),.48,M['white'],FONTIT)
# resort identity text on central facade
text('Santorini_CN','圣托利庄园',(0,-.78,12.95),.78,M['gold_dark'],FONT)
text('Santorini_EN','SANTORINI HOT SPRING RESORT',(0,-.80,12.25),.40,M['gold_dark'],FONT)
text('Guangzhou_CN','GUANGZHOU · GUANGDONG',(0,-.81,11.70),.22,M['gold_dark'],FONT)
# decorative sign underline
box('Resort_sign_underline',(0,-.83,11.98),(6.8,.08,.06),M['gold_dark'],'sign',.01,'EXT_01_front')
# doors side cafe / umbrellas as architectural elements
for side in [-1,1]:
    for i in range(2):
        x=side*(10.0+i*3.7); box(f'Side_door_{side}_{i}',(x,-.7,2.0),(2.0,.08,3.1),M['glass_warm'],'glass',.02,'EXT_02_front')
        arch_ring(f'Side_door_arch_{side}_{i}',x,.8,2.3,4.1,M['cyan'],None,front=-.78,key='arch')
# steps and paving
for i in range(4): box(f'Entrance_step_{i}',(0,-1.55-i*.33,.10+i*.13),(8.1+i*.28,.75+i*.32,.20),M['stone'],'steps',.035,'DETAIL_entrance')
# lights
def point(n,loc,energy,col=(1,.55,.22),soft=.2):
    d=bpy.data.lights.new(n,'POINT'); d.energy=energy; d.color=col; d.shadow_soft_size=soft; o=bpy.data.objects.new(n,d); COL['lighting'].objects.link(o); o.location=loc; return tag(o,n,'photo-lighting',False)
for i,x in enumerate([-13,-7,-3,3,7,13]): point(f'Warm_store_light_{i}',(x,-1.3,4.1),90)
for i,x in enumerate([-12,-6,6,12]): point(f'Warm_upper_light_{i}',(x,-1.0,8.4),80)
# preview studio and scene metadata
scene=bpy.context.scene; scene.unit_settings.system='METRIC'; scene.unit_settings.length_unit='METERS'; scene['model_scope']='McDonald\'s Santorini Hot Spring Resort facade and host building; no context'; scene['dimensional_accuracy']='L1 photo-estimated, not surveyed'; scene['store_name']=CFG['store_name']; scene['city']=CFG['city_cn']; scene['address']=CFG['address']; scene['style']='Santorini-inspired resort facade with classical arched openings'; scene['photo_credits']='Eight supplied user photographs'
for i,(n,d) in enumerate([('REF_01_front','Front elevation with tower, bell, resort sign and entrance'),('REF_02_oblique','Three-quarter front and glass elevator'),('REF_03_side_windows','Long side elevation with repeated cyan arched windows'),('REF_04_tower','Bell tower and statues'),('REF_05_wide','Full facade context'),('REF_06_detail','Entrance and signage'),('REF_07_side','Side McDonald\'s sign and patio'),('REF_08_rear_side','Rear/side parapet completion')]): o=bpy.data.objects.new(n,None); COL['ref'].objects.link(o); o.empty_display_type='PLAIN_AXES'; o.hide_render=True; o['description']=d; o['source']='supplied user photograph'
box('Studio_ground',(0,6,-.16),(120,120,.12),M['ground'],'studio',.02,'preview only')
world=bpy.data.worlds.new('Neutral_studio_world'); scene.world=world; world.use_nodes=True; bg=world.node_tree.nodes.get('Background') or world.node_tree.nodes.new('ShaderNodeBackground'); bg.inputs[0].default_value=(.055,.07,.09,1); bg.inputs[1].default_value=.30
def area(n,loc,pow,size,col,target): d=bpy.data.lights.new(n,'AREA'); d.energy=pow; d.shape='DISK'; d.size=size; d.color=col; o=bpy.data.objects.new(n,d); COL['studio'].objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
area('Studio_key',(-20,-22,23),2200,11,(1,.82,.64),(0,2,7)); area('Studio_fill',(20,-14,15),1800,10,(.65,.80,1),(0,4,7)); area('Studio_rim',(0,16,22),2600,9,(1,.93,.82),(0,4,9))
def camera(n,loc,target,ortho): d=bpy.data.cameras.new(n); d.type='ORTHO'; d.ortho_scale=ortho; o=bpy.data.objects.new(n,d); COL['studio'].objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
CAMS={'01_front':camera('CAM_01_front',(0,-42,9),(0,1,8),23),'02_oblique':camera('CAM_02_oblique',(27,-37,19),(0,3,8),29),'03_detail':camera('CAM_03_detail',(10,-25,7),(0,-.4,5),14),'04_night':camera('CAM_04_night',(-24,-35,16),(0,2,8),27)}
scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.resolution_x=CFG['render']['resolution_x']; scene.render.resolution_y=CFG['render']['resolution_y']; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False; scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
readme=bpy.data.texts.new('READ_ME_MODEL_GUIDE'); readme.write('McDonald\'s Santorini Hot Spring Resort Guangzhou\nUnit: metres. Accuracy L1 photo-estimated, not surveyed.\nCollections 01-07 are deliverables; 90 preview studio and 99 metadata excluded from exports.\nEdit src/santorini_config.json and rerun build_santorini.py.\n')
scene.camera=CAMS['02_oblique']; blend=os.path.join(MODELS,'Santorini_Hot_Spring_Resort_McDonalds.blend'); bpy.ops.wm.save_as_mainfile(filepath=blend)
# export deliverable collections
export=[]
for k in ['shell','stone','arch','glass','sign','steps','lighting']: export += [o for o in COL[k].objects if o.type in {'MESH','CURVE','FONT','LIGHT'}]
bpy.ops.object.select_all(action='DESELECT')
for o in export: o.select_set(True)
if export: bpy.context.view_layer.objects.active=export[0]
for o in list(export):
    if o.type in {'CURVE','FONT'}:
        o.select_set(True); bpy.context.view_layer.objects.active=o
        try: bpy.ops.object.convert(target='MESH')
        except: pass
        o.select_set(False)
export=[o for o in export if o.name in bpy.data.objects]
bpy.ops.object.select_all(action='DESELECT')
for o in export: o.select_set(True)
if export: bpy.context.view_layer.objects.active=export[0]
bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS,'Santorini_Hot_Spring_Resort_McDonalds.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT',export_extras=True)
meshes=[o for o in export if o.type=='MESH']; bpy.ops.object.select_all(action='DESELECT'); [o.select_set(True) for o in meshes]
if meshes: bpy.context.view_layer.objects.active=meshes[0]; bpy.ops.wm.obj_export(filepath=os.path.join(MODELS,'Santorini_Hot_Spring_Resort_McDonalds.obj'),export_selected_objects=True,apply_modifiers=True,export_materials=True,path_mode='COPY')
try: bpy.ops.export_scene.fbx(filepath=os.path.join(MODELS,'Santorini_Hot_Spring_Resort_McDonalds.fbx'),use_selection=True,use_mesh_modifiers=True,add_leaf_bones=False)
except Exception as e: print('FBX warning',e)
# renders
for k,cam in CAMS.items():
    scene.camera=cam
    if k=='04_night': bg.inputs[0].default_value=(.006,.009,.015,1); bg.inputs[1].default_value=.055
    else: bg.inputs[0].default_value=(.055,.07,.09,1); bg.inputs[1].default_value=.30
    scene.render.filepath=os.path.join(PREV,'Santorini_'+k+'.png'); bpy.ops.render.render(write_still=True)
# manifest
stats={'project':CFG['project'],'store_name':CFG['store_name'],'city':CFG['city_cn'],'address':CFG['address'],'accuracy_level':'L1','units':'metres','dimensions_m':{'width':B['width'],'depth':B['depth'],'main_height':B['main_height'],'tower_height':B['tower_height'],'overall_height':B['tower_height'],'frontage_to_depth_ratio':round(B['width']/B['depth'],3)},'collections':{},'exports':['Santorini_Hot_Spring_Resort_McDonalds.blend','Santorini_Hot_Spring_Resort_McDonalds.glb','Santorini_Hot_Spring_Resort_McDonalds.obj','Santorini_Hot_Spring_Resort_McDonalds.mtl','Santorini_Hot_Spring_Resort_McDonalds.fbx'],'export_excluded_collection':'90_PREVIEW_STUDIO_EXCLUDED_FROM_EXPORT','notes':CFG['notes'],'source_photos':['EXT_01_front.jpg','EXT_02_oblique.jpg','DETAIL_01_entrance.jpg','EXT_03_side.jpg','EXT_04_tower.jpg','EXT_05_wide.jpg','EXT_06_signage.jpg','EXT_07_entrance_detail.jpg']}
for k,c in COL.items(): stats['collections'][c.name]={'objects':len(c.objects),'exported':k not in {'studio','ref'}}
with open(os.path.join(MODELS,'model_manifest.json'),'w',encoding='utf-8') as f: json.dump(stats,f,ensure_ascii=False,indent=2)
print('BUILD_COMPLETE',json.dumps(stats,ensure_ascii=False))







