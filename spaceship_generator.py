#+
# spaceship_generator.py
#
# This is a Blender script that uses procedural generation to create
# textured 3D spaceship models. Tested with Blender 2.82.
#
# michael@spaceduststudios.com, Lawrence D'Oliveiro
# https://github.com/ldo/SpaceshipGenerator
#-

import os
import bpy
import bmesh
import math
from mathutils import \
    Matrix, \
    Vector
from random import \
    Random
import enum
from colorsys import \
    hls_to_rgb

deg = math.pi / 180 # angle unit conversion factor

DIR = os.path.dirname(os.path.abspath(__file__))

def resource_path(*path_components) :
    return os.path.join(DIR, *path_components)
#end resource_path

def load_image(filename, use_alpha, is_color) :
    name = os.path.splitext(filename)[0]
    filepath = resource_path("textures", filename)
    image = bpy.data.images.load(filepath)
    image.alpha_mode = ("NONE", "STRAIGHT")[use_alpha]
    image.colorspace_settings.name = ("Non-Color", "sRGB")[is_color]
    image.pack()
    # wipe all traces of original addon file path
    image.filepath = "//textures/%s" % filename
    image.filepath_raw = image.filepath
    for item in image.packed_files :
        item.filepath = image.filepath
    #end for
    return image
#end load_image

class NodeContext :
    "convenience class for assembling a nicely-laid-out node graph."

    def __init__(self, graph, location, clear = False) :
        "“graph” is the node tree for which to manage the addition of nodes." \
        " “location” is the initial location at which to start placing new nodes." \
        " clear indicates whether to get rid of any existing nodes or not."
        self.graph = graph
        self._location = [location[0], location[1]]
        if clear :
            for node in self.graph.nodes :
                self.graph.nodes.remove(node)
            #end for
        #end if
    #end __init__

    def step_across(self, width) :
        "returns the current position and advances it across by width."
        result = self._location[:]
        self._location[0] += width
        return result
    #end step_across

    def step_down(self, height) :
        "returns the current position and advances it down by height."
        result = self._location[:]
        self._location[1] -= height
        return result
     #end step_down

    @property
    def pos(self) :
        "the current position (read/write)."
        return (self._location[0], self._location[1])
    #end pos

    @pos.setter
    def pos(self, pos) :
        self._location[:] = [pos[0], pos[1]]
    #end pos

    def node(self, type, pos) :
        "creates a new node of type “type” at position “pos”, and returns it."
        node = self.graph.nodes.new(type)
        node.location = (pos[0], pos[1])
        return node
    #end node

    def link(self, frôm, to) :
        "creates a link from output “frôm” to input “to”."
        self.graph.links.new(frôm, to)
    #end link

#end NodeContext

def deselect_all(material_tree) :
    for node in material_tree.nodes :
        node.select = False
    #end for
#end deselect_all

def scale_face(bm, face, scale_x, scale_y, scale_z) :
    # Scales a face in local face space. Ace!
    face_space = get_face_matrix(face)
    face_space.invert()
    bmesh.ops.scale \
      (
        bm,
        vec = Vector((scale_x, scale_y, scale_z)),
        space = face_space,
        verts = face.verts
      )
#end scale_face

def extrude_face(bm, face, translate_forwards = 0.0, extruded_face_list = None) :
    # Extrudes a face along its normal by translate_forwards units.
    # Returns the new face, and optionally fills out extruded_face_list
    # with all the additional side faces created from the extrusion.
    new_faces = bmesh.ops.extrude_discrete_faces(bm, faces = [face])["faces"]
    if extruded_face_list != None :
        extruded_face_list += new_faces[:]
    #end if
    new_face = new_faces[0]
    bmesh.ops.translate \
      (
        bm,
        vec = new_face.normal * translate_forwards,
        verts = new_face.verts
      )
    return new_face
#end extrude_face

def ribbed_extrude_face(bm, face, translate_forwards, num_ribs = 3, rib_scale = 0.9) :
    # Similar to extrude_face, except corrigates the geometry to create "ribs".
    # Returns the new face.
    translate_forwards_per_rib = translate_forwards / num_ribs
    new_face = face
    for i in range(num_ribs) :
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.25)
        new_face = extrude_face(bm, new_face, 0.0)
        scale_face(bm, new_face, rib_scale, rib_scale, rib_scale)
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.5)
        new_face = extrude_face(bm, new_face, 0.0)
        scale_face(bm, new_face, 1 / rib_scale, 1 / rib_scale, 1 / rib_scale)
        new_face = extrude_face(bm, new_face, translate_forwards_per_rib * 0.25)
    #end for
    return new_face
#end ribbed_extrude_face

def get_face_matrix(face, pos = None) :
    # Returns a rough 4x4 transform matrix for a face (doesn't handle
    # distortion/shear) with optional position override.
    x_axis = (face.verts[1].co - face.verts[0].co).normalized()
    z_axis = -face.normal
    y_axis = z_axis.cross(x_axis)
    if not pos :
        pos = face.calc_center_bounds()
    #end if

    # Construct a 4x4 matrix from axes + position:
    # http://i.stack.imgur.com/3TnQP.png
    mat = Matrix()
    mat[0][0] = x_axis.x
    mat[1][0] = x_axis.y
    mat[2][0] = x_axis.z
    mat[3][0] = 0
    mat[0][1] = y_axis.x
    mat[1][1] = y_axis.y
    mat[2][1] = y_axis.z
    mat[3][1] = 0
    mat[0][2] = z_axis.x
    mat[1][2] = z_axis.y
    mat[2][2] = z_axis.z
    mat[3][2] = 0
    mat[0][3] = pos.x
    mat[1][3] = pos.y
    mat[2][3] = pos.z
    mat[3][3] = 1
    return mat
#end get_face_matrix

def get_face_width_and_height(face) :
    # Returns the rough length and width of a quad face.
    # Assumes a perfect rectangle, but close enough.
    if not face.is_valid or len(face.verts[:]) < 4 :
        return -1, -1
    #end if
    width = (face.verts[0].co - face.verts[1].co).length
    height = (face.verts[2].co - face.verts[1].co).length
    return width, height
#end get_face_width_and_height

def get_aspect_ratio(face) :
    # Returns the rough aspect ratio of a face. Always >= 1.
    if not face.is_valid :
        return 1.0
    #end if
    face_aspect_ratio = max(0.01, face.edges[0].calc_length() / face.edges[1].calc_length())
    if face_aspect_ratio < 1.0 :
        face_aspect_ratio = 1.0 / face_aspect_ratio
    #end if
    return face_aspect_ratio
#end get_aspect_ratio

def is_rear_face(face) :
    # is this face pointing behind the ship
    return face.normal.x < -0.95
#end is_rear_face

class MATERIAL(enum.IntEnum) :
    "names for material slot indices. Must be densely-assigned from 0."
    HULL = 0            # Plain spaceship hull
    HULL_LIGHTS = 1     # Spaceship hull with emissive windows
    HULL_DARK = 2       # Plain Spaceship hull, darkened
    HULL_METALLIC = 3   # Metallic parts (antennas)
    EXHAUST_BURN = 4    # Emissive engine burn material
    GLOW_DISC = 5       # Emissive landing pad disc material
#end MATERIAL

def create_materials(parms) :
    # Creates all our materials and returns them as a list.

    def define_tex_coords_common() :
        # creates a node group that defines a common coordinate system
        # for all my image textures.
        tex_coords_common = bpy.data.node_groups.new("SpaceShip.TexCoordsCommon", "ShaderNodeTree")
        ctx = NodeContext(tex_coords_common, (-100, 0))
        tex_coords = ctx.node("ShaderNodeTexCoord", ctx.step_across(200))
        group_output = ctx.node("NodeGroupOutput", ctx.step_across(200))
        tex_coords_common.outputs.new("NodeSocketVector", "Coords")
          # work around intermittent crash on following line
        ctx.link(tex_coords.outputs["Generated"], group_output.inputs[0])
        group_output.inputs[0].name = tex_coords_common.outputs[0].name
        return tex_coords_common
    #end define_tex_coords_common

    tex_coords_common = define_tex_coords_common()

    def define_hull_color_common() :
        # creates a node group that applies the grunge factor to
        # an input colour to produce an output colour.
        hull_common = bpy.data.node_groups.new("SpaceShip.HullColorCommon", "ShaderNodeTree")
        ctx = NodeContext(hull_common, (-400, 0))
        save_pos = ctx.pos
        group_input = ctx.node("NodeGroupInput", ctx.step_down(200))
        hull_common.inputs.new("NodeSocketColor", "Color")
        hull_common.inputs.new("NodeSocketFloat", "Grunge")
        hull_common.inputs[1].default_value = parms.grunge_factor
        dirty = ctx.node("ShaderNodeTexNoise", ctx.step_across(200))
        dirty.inputs["Scale"].default_value = 20
        dirtier = ctx.node("ShaderNodeBrightContrast", ctx.step_across(200))
        ctx.link(dirty.outputs[0], dirtier.inputs[0])
        dirtier.inputs[2].default_value = 2
        ctx.pos = (ctx.pos[0], save_pos[1])
        mix = ctx.node("ShaderNodeMixRGB", ctx.step_across(200))
        mix.blend_type = "MULTIPLY"
        ctx.link(group_input.outputs[1], mix.inputs[0])
        ctx.link(group_input.outputs[0], mix.inputs[1])
        ctx.link(dirtier.outputs[0], mix.inputs[2])
        group_output = ctx.node("NodeGroupOutput", ctx.step_across(200))
        hull_common.outputs.new("NodeSocketColor", "Color")
        ctx.link(mix.outputs[0], group_output.inputs[0])
        group_input.outputs[0].name = hull_common.inputs[0].name
        group_input.outputs[1].name = hull_common.inputs[1].name
        group_output.inputs[0].name = hull_common.outputs[0].name
        deselect_all(hull_common)
        return hull_common
    #end define_hull_color_common

    hull_color_common = define_hull_color_common()

    def create_texture(ctx, filename, use_alpha, is_color) :
        # Creates an image texture node given filename relative to my
        # “textures” subdirectory. Returns the output terminal to be linked
        # to wherever the texture colour is needed.
        img = load_image(filename, use_alpha, is_color)
        coords = ctx.node("ShaderNodeGroup", ctx.step_across(200))
        coords.node_tree = tex_coords_common
        tex = ctx.node("ShaderNodeTexImage", ctx.step_across(300))
        tex.image = img
        tex.projection = "BOX"
        ctx.link(coords.outputs[0], tex.inputs[0])
        return tex.outputs["Color"]
    #end create_texture

    def define_normals_common() :
        # defines a node group for the normal-mapping texture to be used
        # across different hull materials.
        normals_common = bpy.data.node_groups.new("SpaceShip.NormalsCommon", "ShaderNodeTree")
        ctx = NodeContext(normals_common, (-300, 0))
        tex_out = create_texture \
          (
            ctx,
            filename = "hull_normal.png",
            use_alpha = True,
            is_color = False
          )
        normal_map = ctx.node("ShaderNodeNormalMap", ctx.step_across(200))
        ctx.link(tex_out, normal_map.inputs["Color"])
        normal_map.inputs["Strength"].default_value = 1
        group_output = ctx.node("NodeGroupOutput", ctx.step_across(200))
        normals_common.outputs.new("NodeSocketVector", "Normal")
          # work around intermittent crash on following line
        ctx.link(normal_map.outputs["Normal"], group_output.inputs[0])
        group_output.inputs[0].name = normals_common.outputs[0].name
        deselect_all(normals_common)
        return normals_common
    #end define_normals_common

    normals_common = define_normals_common()

    def hull_mat_common(ctx, base_color) :
        # common setup for various hull materials.
        save_pos = ctx.pos
        color_mix = ctx.node("ShaderNodeGroup", ctx.step_down(200))
        color_mix.node_tree = hull_color_common
        color_mix.inputs["Color"].default_value = tuple(base_color) + (1,)
        normal_map = ctx.node("ShaderNodeGroup", ctx.step_across(200))
        normal_map.node_tree = normals_common
        ctx.pos = (ctx.pos[0], save_pos[1])
        save_pos = ctx.pos
        ctx.step_down(200)
        normals_fanout = ctx.node("NodeReroute", ctx.step_across(100))
        ctx.link(normal_map.outputs[0], normals_fanout.inputs[0])
        ctx.pos = (ctx.pos[0], save_pos[1])
        save_pos = ctx.pos
        color_shader = ctx.node("ShaderNodeBsdfDiffuse", ctx.step_down(200))
        ctx.link(color_mix.outputs[0], color_shader.inputs["Color"])
        ctx.link(normals_fanout.outputs[0], color_shader.inputs["Normal"])
        shiny = ctx.node("ShaderNodeBsdfGlossy", ctx.step_across(200))
        shiny.inputs["Roughness"].default_value = 0.5
        ctx.link(normals_fanout.outputs[0], shiny.inputs["Normal"])
        ctx.pos = (ctx.pos[0], save_pos[1])
        mix_shader = ctx.node("ShaderNodeMixShader", ctx.step_across(200))
        mix_shader.inputs[0].default_value = 0.1
        ctx.link(color_shader.outputs[0], mix_shader.inputs[1])
        ctx.link(shiny.outputs[0], mix_shader.inputs[2])
        return mix_shader.outputs[0]
    #end hull_mat_common

    def set_hull_mat_basics(mat, base_color) :
        # Sets some basic properties for a hull material.
        ctx = NodeContext(mat.node_tree, (-450, 0), clear = True)
        shader_output = hull_mat_common(ctx, base_color)
        material_output = ctx.node("ShaderNodeOutputMaterial", ctx.step_across(200))
        ctx.link(shader_output, material_output.inputs[0])
        deselect_all(mat.node_tree)
    #end set_hull_mat_basics

    def set_hull_mat_emissive(mat, color, strength) :
        # does common setup for very basic emissive hull materials (engines, landing discs)
        ctx = NodeContext(mat.node_tree, (-200, 0), clear = True)
        emit = ctx.node("ShaderNodeEmission", ctx.step_across(200))
        emit.inputs["Color"].default_value = tuple(color) + (1,)
        emit.inputs["Strength"].default_value = strength
        material_output = ctx.node("ShaderNodeOutputMaterial", ctx.step_across(200))
        ctx.link(emit.outputs[0], material_output.inputs[0])
        deselect_all(mat.node_tree)
    #end set_hull_mat_emissive

#begin create_materials

    materials = []
    for material in MATERIAL :
        mat = bpy.data.materials.new(material.name.lower())
        mat.use_nodes = True
        materials.append(mat)
    #end for

    # Build the hull texture
    set_hull_mat_basics(materials[MATERIAL.HULL], parms.hull_base_color)

    ctx = NodeContext(materials[MATERIAL.HULL_LIGHTS].node_tree, (-600, 0), clear = True)
    save1_pos = ctx.pos
    base_output = hull_mat_common(ctx, parms.hull_base_color)
    save2_pos = ctx.pos
    ctx.pos = save1_pos
    ctx.step_down(450)
    # Add an emissive layer that lights up the windows
    window_light = create_texture \
      (
        ctx,
        filename = "hull_lights_emit.png",
        use_alpha = False,
        is_color = True
      )
    brighter = ctx.node("ShaderNodeMath", ctx.step_across(200))
    brighter.operation = "MULTIPLY"
    ctx.link(window_light, brighter.inputs[0])
    brighter.inputs[1].default_value = 2.0
    light_shader = ctx.node("ShaderNodeEmission", ctx.step_across(200))
    light_shader.inputs["Color"].default_value = tuple(parms.hull_emissive_color) + (1,)
    ctx.link(brighter.outputs[0], light_shader.inputs["Strength"])
    ctx.pos = save2_pos
    add_shader = ctx.node("ShaderNodeAddShader", ctx.step_across(200))
    ctx.link(base_output, add_shader.inputs[0])
    ctx.link(light_shader.outputs[0], add_shader.inputs[1])
    material_output = ctx.node("ShaderNodeOutputMaterial", ctx.step_across(200))
    ctx.link(add_shader.outputs[0], material_output.inputs[0])
    deselect_all(ctx.graph)

    # Build the hull_dark texture
    set_hull_mat_basics \
      (
        materials[MATERIAL.HULL_DARK],
        tuple(parms.hull_darken * x for x in parms.hull_base_color[:3])
      )

    # build the metallic material
    ctx = NodeContext(materials[MATERIAL.HULL_METALLIC].node_tree, (-200, 0), clear = True)
    color_mix = ctx.node("ShaderNodeGroup", ctx.step_across(200))
    color_mix.node_tree = hull_color_common
    color_mix.inputs["Color"].default_value = hls_to_rgb(h = 0.091, l = 0.9, s = 0.1) + (1,)
    shiny = ctx.node("ShaderNodeBsdfGlossy", ctx.step_across(200))
    ctx.link(color_mix.outputs[0], shiny.inputs["Color"])
    shiny.inputs["Roughness"].default_value = 0.4
    material_output = ctx.node("ShaderNodeOutputMaterial", ctx.step_across(200))
    ctx.link(shiny.outputs[0], material_output.inputs[0])

    # Build the exhaust_burn texture
    set_hull_mat_emissive(materials[MATERIAL.EXHAUST_BURN], parms.glow_color, 1.0)

    # Build the glow_disc texture
    set_hull_mat_emissive(materials[MATERIAL.GLOW_DISC], parms.glow_color, 1.0)

    return materials
#end create_materials

class ALIGN_TO(enum.Enum) :
    "Aligning the orientation of a newly-created spaceship."
    NONE = "nothing"
    WORLD = "world"
    VIEW = "view"
    CURSOR = "cursor"

    @property
    def idstr(self) :
        return \
            self.value
    #end idstr

#end ALIGN_TO

class parms_defaults :
    "define parameter defaults in a single place for reuse."
    geom_ranseed = ""
    align = ALIGN_TO.NONE.idstr
    mat_ranseed = ""
    num_hull_segments_min = 3
    num_hull_segments_max = 6
    create_asymmetry_segments = True
    num_asymmetry_segments_min = 1
    num_asymmetry_segments_max = 5
    create_face_detail = True
    allow_horizontal_symmetry = True
    allow_vertical_symmetry = False
    add_bevel_modifier = True
    create_materials = True
    hull_base_color = (0.5, 0.5, 0.5)
    hull_darken = 0.3
    hull_emissive_color = (0.75, 0.75, 0.75)
    glow_color = (1, 1, 1)
    grunge_factor = 0.5
#end parms_defaults

def randomize_colors(parms, mat_random) :
    # Choose a base color for the spaceship hull
    parms.hull_base_color = hls_to_rgb \
      (
        h = mat_random.random(),
        l = mat_random.uniform(0.05, 0.5),
        s = mat_random.uniform(0, 0.25)
      )
    parms.hull_emissive_color = hls_to_rgb \
      (
        h = mat_random.random(),
        l = mat_random.uniform(0.5, 1),
        s = mat_random.uniform(0, 0.5)
      )
    # Choose a glow color for the exhaust + glow discs
    parms.glow_color = hls_to_rgb(h = mat_random.random(), l = mat_random.uniform(0.5, 1), s = 1)
#end randomize_colors

def generate_spaceship(parms) :
    # Generates a textured spaceship mesh and returns the object.
    # Just uses global cube texture coordinates rather than generating UVs.
    # Takes an optional random seed value to generate a specific spaceship.
    # Allows overriding of some parameters that affect generation.
    geom_random = Random()
    if parms.geom_ranseed != "" :
        geom_random.seed(parms.geom_ranseed)
    #end if

    def add_exhaust_to_face(bm, face) :
        # Given a face, splits it into a uniform grid and extrudes each grid face
        # out and back in again, making an exhaust shape.
        if not face.is_valid :
            return
        #end if

        # The more square the face is, the more grid divisions it might have
        num_cuts = geom_random.randint(1, int(4 - get_aspect_ratio(face)))
        result = bmesh.ops.subdivide_edges \
          (
            bm,
            edges = face.edges[:],
            cuts = num_cuts,
            fractal = 0.02,
            use_grid_fill = True
          )
        exhaust_length = geom_random.uniform(0.1, 0.2)
        scale_outer = 1 / geom_random.uniform(1.3, 1.6)
        scale_inner = 1 / geom_random.uniform(1.05, 1.1)
        for face in result["geom"] :
            if isinstance(face, bmesh.types.BMFace) :
                if is_rear_face(face) :
                    face.material_index = MATERIAL.HULL_DARK
                    face = extrude_face(bm, face, exhaust_length)
                    scale_face(bm, face, scale_outer, scale_outer, scale_outer)
                    extruded_face_list = []
                    face = extrude_face(bm, face, -exhaust_length * 0.9, extruded_face_list)
                    for extruded_face in extruded_face_list :
                        extruded_face.material_index = MATERIAL.EXHAUST_BURN
                    #end for
                    scale_face(bm, face, scale_inner, scale_inner, scale_inner)
                #end if
            #end if
        #end for
    #end add_exhaust_to_face

    def add_grid_to_face(bm, face) :
        # Given a face, splits it up into a smaller uniform grid and extrudes each grid cell.
        if not face.is_valid :
            return
        #end if
        result = bmesh.ops.subdivide_edges \
          (
            bm,
            edges = face.edges[:],
            cuts = geom_random.randint(2, 4),
            fractal = 0.02,
            use_grid_fill = True,
            use_single_edge = False
          )
        grid_length = geom_random.uniform(0.025, 0.15)
        scale = 0.8
        for face in result["geom"] :
            if isinstance(face, bmesh.types.BMFace) :
                material_index = MATERIAL.HULL_LIGHTS if geom_random.random() > 0.5 else MATERIAL.HULL
                extruded_face_list = []
                face = extrude_face(bm, face, grid_length, extruded_face_list)
                for extruded_face in extruded_face_list :
                    if abs(face.normal.z) < 0.707 : # side face
                        extruded_face.material_index = material_index
                    #end if
                #end for
                scale_face(bm, face, scale, scale, scale)
            #end if
        #end for
    #end add_grid_to_face

    def add_cylinders_to_face(bm, face) :
        # Given a face, adds some cylinders along it in a grid pattern.
        if not face.is_valid or len(face.verts[:]) < 4 :
            return
        #end if
        horizontal_step = geom_random.randint(1, 3)
        vertical_step = geom_random.randint(1, 3)
        num_segments = geom_random.randint(6, 12)
        face_width, face_height = get_face_width_and_height(face)
        cylinder_depth = \
          (
                1.3
            *
                min
                  (
                    face_width / (horizontal_step + 2),
                    face_height / (vertical_step + 2)
                  )
          )
        cylinder_size = cylinder_depth * 0.5
        for h in range(horizontal_step) :
            top = face.verts[0].co.lerp \
              (
                face.verts[1].co,
                (h + 1) / (horizontal_step + 1)
              )
            bottom = face.verts[3].co.lerp \
              (
                face.verts[2].co,
                (h + 1) / (horizontal_step + 1)
              )
            for v in range(vertical_step) :
                pos = top.lerp(bottom, (v + 1) / (vertical_step + 1))
                cylinder_matrix = \
                  (
                        get_face_matrix(face, pos)
                    @
                        Matrix.Rotation(90 * deg, 3, "X").to_4x4()
                  )
                bmesh.ops.create_cone \
                  (
                    bm,
                    cap_ends = True,
                    cap_tris = False,
                    segments = num_segments,
                    diameter1 = cylinder_size,
                    diameter2 = cylinder_size,
                    depth = cylinder_depth,
                    matrix = cylinder_matrix
                  )
            #end for
        #end for
    #end add_cylinders_to_face

    def add_weapons_to_face(bm, face) :
        # Given a face, adds some weapon turrets to it in a grid pattern.
        # Each turret will have a random orientation.
        if not face.is_valid or len(face.verts[:]) < 4 :
            return
        #end if
        horizontal_step = geom_random.randint(1, 2)
        vertical_step = geom_random.randint(1, 2)
        num_segments = 16
        face_width, face_height = get_face_width_and_height(face)
        weapon_size = \
          (
                0.5
            *
                min
                  (
                    face_width / (horizontal_step + 2),
                    face_height / (vertical_step + 2)
                  )
          )
        weapon_depth = weapon_size * 0.2
        for h in range(horizontal_step) :
            top = face.verts[0].co.lerp \
              (
                face.verts[1].co,
                (h + 1) / (horizontal_step + 1)
              )
            bottom = face.verts[3].co.lerp \
              (
                face.verts[2].co,
                (h + 1) / (horizontal_step + 1)
              )
            for v in range(vertical_step) :
                pos = top.lerp(bottom, (v + 1) / (vertical_step + 1))
                face_matrix = \
                  (
                        get_face_matrix(face, pos + face.normal * weapon_depth * 0.5)
                    @
                        Matrix.Rotation(geom_random.uniform(0, 90) * deg, 3, "Z").to_4x4()
                  )

                # Turret foundation
                bmesh.ops.create_cone \
                  (
                    bm,
                    cap_ends = True,
                    cap_tris = False,
                    segments = num_segments,
                    diameter1 = weapon_size * 0.9,
                    diameter2 = weapon_size,
                    depth = weapon_depth,
                    matrix = face_matrix
                  )
                # Turret left guard
                bmesh.ops.create_cone \
                  (
                    bm,
                    cap_ends = True,
                    cap_tris = False,
                    segments = num_segments,
                    diameter1 = weapon_size * 0.6,
                    diameter2 = weapon_size * 0.5,
                    depth = weapon_depth * 2,
                    matrix =
                            face_matrix
                        @
                            Matrix.Rotation(90 * deg, 3, "Y").to_4x4()
                        @
                            Matrix.Translation(Vector((0, 0, weapon_size * 0.6))).to_4x4()
                  )
                # Turret right guard
                bmesh.ops.create_cone \
                  (
                    bm,
                    cap_ends = True,
                    cap_tris = False,
                    segments = num_segments,
                    diameter1 = weapon_size * 0.5,
                    diameter2 = weapon_size * 0.6,
                    depth = weapon_depth * 2,
                    matrix =
                            face_matrix
                        @
                            Matrix.Rotation(90 * deg, 3, "Y").to_4x4()
                        @
                            Matrix.Translation(Vector((0, 0, weapon_size * -0.6))).to_4x4()
                  )
                # Turret housing
                upward_angle = geom_random.uniform(0, 45) * deg
                turret_house_mat = \
                  (
                        face_matrix
                    @
                        Matrix.Rotation(upward_angle, 3, "X").to_4x4()
                    @
                        Matrix.Translation(Vector((0, weapon_size * -0.4, 0))).to_4x4()
                  )
                bmesh.ops.create_cone \
                  (
                    bm,
                    cap_ends = True,
                    cap_tris = False,
                    segments = 8,
                    diameter1 = weapon_size * 0.4,
                    diameter2 = weapon_size * 0.4,
                    depth = weapon_depth * 5,
                    matrix = turret_house_mat
                  )
                # Turret barrels L + R
                bmesh.ops.create_cone \
                  (
                    bm,
                    cap_ends = True,
                    cap_tris = False,
                    segments = 8,
                    diameter1 = weapon_size * 0.1,
                    diameter2 = weapon_size * 0.1,
                    depth = weapon_depth * 6,
                    matrix =
                            turret_house_mat
                        @
                            Matrix.Translation(Vector((weapon_size * 0.2, 0, -weapon_size))).to_4x4()
                  )
                bmesh.ops.create_cone \
                  (
                    bm,
                    cap_ends = True,
                    cap_tris = False,
                    segments = 8,
                    diameter1 = weapon_size * 0.1,
                    diameter2 = weapon_size * 0.1,
                    depth = weapon_depth * 6,
                    matrix =
                            turret_house_mat
                        @
                            Matrix.Translation(Vector((weapon_size * -0.2, 0, -weapon_size))).to_4x4()
                  )
            #end for v in range(vertical_step)
        #end for h in range(horizontal_step)
    #end add_weapons_to_face

    def add_sphere_to_face(bm, face) :
        # Given a face, adds a sphere on the surface, partially inset.
        if not face.is_valid :
            return
        #end if
        face_width, face_height = get_face_width_and_height(face)
        sphere_size = geom_random.uniform(0.4, 1.0) * min(face_width, face_height)
        sphere_matrix = get_face_matrix \
          (
            face,
            face.calc_center_bounds() - face.normal * geom_random.uniform(0, sphere_size * 0.5)
          )
        result = bmesh.ops.create_icosphere \
          (
            bm,
            subdivisions = 3,
            diameter = sphere_size,
            matrix = sphere_matrix
          )
        for vert in result["verts"] :
            for face in vert.link_faces :
                face.material_index = MATERIAL.HULL
            #end for
        #end for
    #end add_sphere_to_face

    def add_surface_antenna_to_face(bm, face) :
        # Given a face, adds some pointy intimidating antennas.
        if not face.is_valid or len(face.verts[:]) < 4 :
            return
        #end if
        horizontal_step = geom_random.randint(4, 10)
        vertical_step = geom_random.randint(4, 10)
        for h in range(horizontal_step) :
            top = face.verts[0].co.lerp \
              (
                face.verts[1].co,
                (h + 1) / (horizontal_step + 1)
              )
            bottom = face.verts[3].co.lerp \
              (
                face.verts[2].co,
                (h + 1) / (horizontal_step + 1)
              )
            for v in range(vertical_step) :
                if geom_random.random() > 0.9 :
                    pos = top.lerp(bottom, (v + 1) / (vertical_step + 1))
                    face_size = math.sqrt(face.calc_area())
                    depth = geom_random.uniform(0.1, 1.5) * face_size
                    depth_short = depth * geom_random.uniform(0.02, 0.15)
                    base_diameter = geom_random.uniform(0.005, 0.05)
                    material_index = MATERIAL.HULL_METALLIC

                    # Spire
                    num_segments = geom_random.uniform(3, 6)
                    result = bmesh.ops.create_cone \
                      (
                        bm,
                        cap_ends = False,
                        cap_tris = False,
                        segments = num_segments,
                        diameter1 = 0,
                        diameter2 = base_diameter,
                        depth = depth,
                        matrix = get_face_matrix(face, pos + face.normal * depth * 0.5)
                      )
                    for vert in result["verts"] :
                        for vert_face in vert.link_faces :
                            vert_face.material_index = material_index
                        #end for
                    #end for

                    # Base
                    result = bmesh.ops.create_cone \
                      (
                        bm,
                        cap_ends = True,
                        cap_tris = False,
                        segments = num_segments,
                        diameter1 = base_diameter * geom_random.uniform(1, 1.5),
                        diameter2 = base_diameter * geom_random.uniform(1.5, 2),
                        depth = depth_short,
                        matrix = get_face_matrix(face, pos + face.normal * depth_short * 0.45)
                      )
                    for vert in result["verts"] :
                        for vert_face in vert.link_faces :
                            vert_face.material_index = material_index
                        #end for
                    #end for
                #end if geom_random.random() > 0.9
            #end for v in range(vertical_step)
        #end for h in range(horizontal_step)
    #end add_surface_antenna_to_face

    def add_disc_to_face(bm, face) :
        # Given a face, adds a glowing "landing pad" style disc.
        if not face.is_valid :
            return
        #end if
        face_width, face_height = get_face_width_and_height(face)
        depth = 0.125 * min(face_width, face_height)
        bmesh.ops.create_cone \
          (
            bm,
            cap_ends = True,
            cap_tris = False,
            segments = 32,
            diameter1 = depth * 3,
            diameter2 = depth * 4,
            depth=depth,
            matrix = get_face_matrix(face, face.calc_center_bounds() + face.normal * depth * 0.5)
          )
        result = bmesh.ops.create_cone \
          (
            bm,
            cap_ends = False,
            cap_tris = False,
            segments = 32,
            diameter1 = depth * 1.25,
            diameter2 = depth * 2.25,
            depth = 0.0,
            matrix = get_face_matrix(face, face.calc_center_bounds() + face.normal * depth * 1.05)
          )
        for vert in result["verts"] :
            for face in vert.link_faces :
                face.material_index = MATERIAL.GLOW_DISC
            #end for
        #end for
    #end add_disc_to_face

#begin generate_spaceship
    # Let's start with a unit BMesh cube scaled randomly
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size = 1)
    scale_vector = Vector \
      ((
        geom_random.uniform(0.75, 2.0),
        geom_random.uniform(0.75, 2.0),
        geom_random.uniform(0.75, 2.0),
      ))
    bmesh.ops.scale(bm, vec = scale_vector, verts = bm.verts)

    # Extrude out the hull along the X axis, adding some semi-random perturbations
    for face in bm.faces[:] :
        if abs(face.normal.x) > 0.5 :
            hull_segment_length = geom_random.uniform(0.3, 1)
            if parms.num_hull_segments_max >= parms.num_hull_segments_min :
                num_hull_segments = geom_random.randrange \
                  (
                    parms.num_hull_segments_min,
                    parms.num_hull_segments_max + 1
                  )
            else :
                num_hull_segments = parms.num_hull_segments_min # or something
            #end if
            hull_segment_range = range(num_hull_segments)
            for i in hull_segment_range :
                is_last_hull_segment = i == hull_segment_range[-1]
                val = geom_random.random()
                if val > 0.1 :
                    # Most of the time, extrude out the face with some random deviations
                    face = extrude_face(bm, face, hull_segment_length)
                    if geom_random.random() > 0.75 :
                        face = extrude_face \
                          (
                            bm,
                            face,
                            translate_forwards = hull_segment_length * 0.25
                          )
                    #end if

                    # Maybe apply some scaling
                    if geom_random.random() > 0.5 :
                        sy = geom_random.uniform(1.2, 1.5)
                        sz = geom_random.uniform(1.2, 1.5)
                        if is_last_hull_segment or geom_random.random() > 0.5 :
                            sy = 1 / sy
                            sz = 1 / sz
                        scale_face(bm, face, 1, sy, sz)
                    #end if

                    # Maybe apply some sideways translation
                    if geom_random.random() > 0.5 :
                        sideways_translation = Vector \
                          (
                            (0, 0, geom_random.uniform(0.1, 0.4) * scale_vector.z * hull_segment_length)
                          )
                        if geom_random.random() > 0.5 :
                            sideways_translation = -sideways_translation
                        #end if
                        bmesh.ops.translate \
                          (
                            bm,
                            vec = sideways_translation,
                            verts = face.verts
                          )
                    #end if

                    # Maybe add some rotation around Y axis
                    if geom_random.random() > 0.5 :
                        angle = 5 * deg
                        if geom_random.random() > 0.5 :
                            angle = -angle
                        #end if
                        bmesh.ops.rotate \
                          (
                            bm,
                            verts = face.verts,
                            cent = (0, 0, 0),
                            matrix = Matrix.Rotation(angle, 3, "Y")
                          )
                    #end if
                else : #  val <= 0.1
                    # Rarely, create a ribbed section of the hull
                    rib_scale = geom_random.uniform(0.75, 0.95)
                    face = ribbed_extrude_face \
                      (
                        bm,
                        face,
                        translate_forwards = hull_segment_length,
                        num_ribs = geom_random.randint(2, 4),
                        rib_scale = rib_scale
                      )
                #end if val > 0.1
            #end for i in hull_segment_range
        #end if abs(face.normal.x) > 0.5
    #end for face in bm.faces[:]

    # Add some large asynmmetrical sections of the hull that stick out
    if (
            parms.create_asymmetry_segments
        and
            parms.num_asymmetry_segments_max >= parms.num_asymmetry_segments_min
    ) :
        for face in bm.faces[:] :
            if (
                    get_aspect_ratio(face) <= 4
                      # Skip any long thin faces as it'll probably look stupid
                and
                    geom_random.random() > 0.85
            ) :
                hull_piece_length = geom_random.uniform(0.1, 0.4)
                for i in \
                    range(geom_random.randrange
                      (
                        parms.num_asymmetry_segments_min,
                        parms.num_asymmetry_segments_max + 1
                      )) \
                :
                    face = extrude_face(bm, face, hull_piece_length)
                    # Maybe apply some scaling
                    if geom_random.random() > 0.25 :
                        s = 1 / geom_random.uniform(1.1, 1.5)
                        scale_face(bm, face, s, s, s)
                    #end if
                #end for
            #end if
        #end for
    #end if

    # Now the basic hull shape is built, let's categorize + add detail to all the faces
    if parms.create_face_detail :
        engine_faces = []
        grid_faces = []
        antenna_faces = []
        weapon_faces = []
        sphere_faces = []
        disc_faces = []
        cylinder_faces = []
        for face in bm.faces[:] :
            # Skip any long thin faces as it'll probably look stupid
            if get_aspect_ratio(face) > 3 :
                continue
            #end if

            # Spin the wheel! Let's categorize + assign some materials
            val = geom_random.random()
            if is_rear_face(face) :
                if not engine_faces or val > 0.75 :
                    engine_faces.append(face)
                elif val > 0.5 :
                    cylinder_faces.append(face)
                elif val > 0.25 :
                    grid_faces.append(face)
                else :
                    face.material_index = MATERIAL.HULL_LIGHTS
                #end if
            elif face.normal.x > 0.9 :  # front face
                if face.normal.dot(face.calc_center_bounds()) > 0 and val > 0.7 :
                    antenna_faces.append(face)  # front facing antenna
                    face.material_index = MATERIAL.HULL_LIGHTS
                elif val > 0.4 :
                    grid_faces.append(face)
                else :
                    face.material_index = MATERIAL.HULL_LIGHTS
                #end if
            elif face.normal.z > 0.9 :  # top face
                if face.normal.dot(face.calc_center_bounds()) > 0 and val > 0.7 :
                    antenna_faces.append(face)  # top facing antenna
                elif val > 0.6 :
                    grid_faces.append(face)
                elif val > 0.3 :
                    cylinder_faces.append(face)
                #end if
            elif face.normal.z < -0.9 :  # bottom face
                if val > 0.75 :
                    disc_faces.append(face)
                elif val > 0.5 :
                    grid_faces.append(face)
                elif val > 0.25 :
                    weapon_faces.append(face)
                #end if
            elif abs(face.normal.y) > 0.9 :  # side face
                if not weapon_faces or val > 0.75 :
                    weapon_faces.append(face)
                elif val > 0.6 :
                    grid_faces.append(face)
                elif val > 0.4 :
                    sphere_faces.append(face)
                else :
                    face.material_index = MATERIAL.HULL_LIGHTS
                #end if
            #end if

        #end for face in bm.faces[:]

        # Now we've categorized, let's actually add the detail
        for face in engine_faces :
            add_exhaust_to_face(bm, face)
        #end for
        for face in grid_faces :
            add_grid_to_face(bm, face)
        #end for
        for face in antenna_faces :
            add_surface_antenna_to_face(bm, face)
        #end for
        for face in weapon_faces :
            add_weapons_to_face(bm, face)
        #end for
        for face in sphere_faces :
            add_sphere_to_face(bm, face)
        #end for
        for face in disc_faces :
            add_disc_to_face(bm, face)
        #end for
        for face in cylinder_faces :
            add_cylinders_to_face(bm, face)
        #end for

    #end if parms.create_face_detail

    # Apply horizontal symmetry sometimes
    if parms.allow_horizontal_symmetry and geom_random.random() > 0.5 :
        bmesh.ops.symmetrize(bm, input = bm.verts[:] + bm.edges[:] + bm.faces[:], direction = "Y")
    #end if
    # Apply vertical symmetry sometimes - this can cause spaceship "islands", so disabled by default
    if parms.allow_vertical_symmetry and geom_random.random() > 0.5 :
        bmesh.ops.symmetrize(bm, input = bm.verts[:] + bm.edges[:] + bm.faces[:], direction = "Z")
    #end if

    # Finish up, write the bmesh into a new mesh
    me = bpy.data.meshes.new("Spaceship")
    bm.to_mesh(me)
    bm.free()

    # Add the mesh to the scene
    obj = bpy.data.objects.new(me.name, me)
    if parms.align == ALIGN_TO.WORLD.idstr :
        orient = Matrix.Identity(4)
    elif parms.align == ALIGN_TO.VIEW.idstr :
        orient = bpy.context.region_data.view_matrix.inverted().decompose()[1].to_matrix()
          # rotation part only
        orient.resize_4x4()
    elif parms.align == ALIGN_TO.CURSOR.idstr :
        orient = bpy.context.scene.cursor.matrix.copy()
    else : # assume ALIGN_TO.NONE
        orient = Matrix.Identity(4)
    #end if
    if parms.align in (ALIGN_TO.VIEW.idstr, ALIGN_TO.CURSOR.idstr) :
        orient = orient @ Matrix.Rotation(-90 * deg, 4, Vector((1, 0, 0)))
    #end if
    if parms.align != ALIGN_TO.NONE.idstr :
        orient = orient @ Matrix.Rotation(-90 * deg, 4, Vector((0, 0, 1)))
    #end if
    if parms.align != ALIGN_TO.CURSOR.idstr :
        orient = Matrix.Translation(bpy.context.scene.cursor.location) @ orient
    #end if
    obj.matrix_basis = orient
    bpy.context.scene.collection.objects.link(obj)

    if parms.add_bevel_modifier :
        # Add a fairly broad bevel modifier to angularize shape
        bevel_modifier = obj.modifiers.new("Bevel", "BEVEL")
        bevel_modifier.width = geom_random.uniform(5, 20)
        bevel_modifier.offset_type = "PERCENT"
        bevel_modifier.segments = 2
        bevel_modifier.profile = 0.25
        bevel_modifier.limit_method = "NONE"
        bevel_modifier.use_clamp_overlap = False # no noticeable effect otherwise
    #end if

    # Add materials to the spaceship
    me = obj.data
    if parms.create_materials :
        materials = create_materials(parms)
        for mat in materials :
            me.materials.append(mat)
        #end for
    else :
        mat = bpy.data.materials.get("Material")
        if mat == None :
            mat = bpy.data.materials.new(name = "Material")
        #end if
        for i in range(len(MATERIAL.__members__)) :
            me.materials.append(mat)
        #end for
    #end if

    # Select and make active
    bpy.ops.object.select_all(action = "DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Recenter the object to its center of mass
    bpy.ops.object.origin_set(type = "ORIGIN_CENTER_OF_MASS")

    return obj
#end generate_spaceship
