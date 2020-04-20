#
# spaceship_generator.py
#
# This is a Blender script that uses procedural generation to create
# textured 3D spaceship models. Tested with Blender 2.79.
#
# michael@spaceduststudios.com
# https://github.com/a1studmuffin/SpaceshipGenerator
#

import os
import bpy
import bmesh
import math
from mathutils import \
    Matrix, \
    Vector
from random import \
    Random
from enum import \
    IntEnum
from colorsys import \
    hls_to_rgb

deg = math.pi / 180 # conversion factor

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

    def __init__(self, graph, location) :
        self.graph = graph
        self.location = [location[0], location[1]]
        self.pos_save = []
    #end __init__

    def step_across(self, width) :
        "returns the current position and advances it across by width."
        result = self.location[:]
        self.location[0] += width
        return result
    #end step_across

    def step_down(self, height) :
        "returns the current position and advances it down by height."
        result = self.location[:]
        self.location[1] -= height
        return result
     #end step_down

    @property
    def pos(self) :
        return (self.location[0], self.location[1])
    #end pos

    @pos.setter
    def pos(self, pos) :
        self.location[:] = [pos[0], pos[1]]
    #end pos

    def push_pos(self) :
        "saves the current location on the stack."
        self.pos_save.append(list(self.location))
    #end push_pos

    def pop_pos(self) :
        "restores the last-stacked location."
        self.location[:] = self.pos_save.pop()
    #end pop_pos

    def new_node(self, type, pos) :
        node = self.graph.nodes.new(type)
        node.location = (pos[0], pos[1])
        return node
    #end new_node

    def link(self, frôm, to) :
        self.graph.links.new(frôm, to)
    #end link

#end NodeContext

def deselect_all(material_tree) :
    for node in material_tree.nodes :
        node.select = False
    #end for
#end deselect_all

def find_main_shader(mat) :
    # returns the main (only) shader node that is created
    # as part of a default material setup.
    return mat.node_tree.nodes["Principled BSDF"]
#end find_main_shader

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
    # is this face is pointing behind the ship
    return face.normal.x < -0.95
#end is_rear_face

class MATERIAL(IntEnum) :
    "names for material slot indices."
    HULL = 0            # Plain spaceship hull
    HULL_LIGHTS = 1     # Spaceship hull with emissive windows
    HULL_DARK = 2       # Plain Spaceship hull, darkened
    EXHAUST_BURN = 3    # Emissive engine burn material
    GLOW_DISC = 4       # Emissive landing pad disc material
#end MATERIAL

def add_exhaust_to_face(bm, face) :
    # Given a face, splits it into a uniform grid and extrudes each grid face
    # out and back in again, making an exhaust shape.
    if not face.is_valid :
        return
    #end if

    # The more square the face is, the more grid divisions it might have
    num_cuts = random.randint(1, int(4 - get_aspect_ratio(face)))
    result = bmesh.ops.subdivide_edges \
      (
        bm,
        edges = face.edges[:],
        cuts = num_cuts,
        fractal = 0.02,
        use_grid_fill = True
      )
    exhaust_length = random.uniform(0.1, 0.2)
    scale_outer = 1 / random.uniform(1.3, 1.6)
    scale_inner = 1 / random.uniform(1.05, 1.1)
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
        cuts = random.randint(2, 4),
        fractal = 0.02,
        use_grid_fill = True,
        use_single_edge = False
      )
    grid_length = random.uniform(0.025, 0.15)
    scale = 0.8
    for face in result["geom"] :
        if isinstance(face, bmesh.types.BMFace) :
            material_index = MATERIAL.HULL_LIGHTS if random.random() > 0.5 else MATERIAL.HULL
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
    horizontal_step = random.randint(1, 3)
    vertical_step = random.randint(1, 3)
    num_segments = random.randint(6, 12)
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
    horizontal_step = random.randint(1, 2)
    vertical_step = random.randint(1, 2)
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
                    Matrix.Rotation(random.uniform(0, 90) * deg, 3, "Z").to_4x4()
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
            upward_angle = random.uniform(0, 45) * deg
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
    sphere_size = random.uniform(0.4, 1.0) * min(face_width, face_height)
    sphere_matrix = get_face_matrix \
      (
        face,
        face.calc_center_bounds() - face.normal * random.uniform(0, sphere_size * 0.5)
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
    horizontal_step = random.randint(4, 10)
    vertical_step = random.randint(4, 10)
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
            if random.random() > 0.9 :
                pos = top.lerp(bottom, (v + 1) / (vertical_step + 1))
                face_size = math.sqrt(face.calc_area())
                depth = random.uniform(0.1, 1.5) * face_size
                depth_short = depth * random.uniform(0.02, 0.15)
                base_diameter = random.uniform(0.005, 0.05)
                material_index = MATERIAL.HULL if random.random() > 0.5 else MATERIAL.HULL_DARK

                # Spire
                num_segments = random.uniform(3, 6)
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
                    diameter1 = base_diameter * random.uniform(1, 1.5),
                    diameter2 = base_diameter * random.uniform(1.5, 2),
                    depth = depth_short,
                    matrix = get_face_matrix(face, pos + face.normal * depth_short * 0.45)
                  )
                for vert in result["verts"] :
                    for vert_face in vert.link_faces :
                        vert_face.material_index = material_index
                    #end for
                #end for
            #end if random.random() > 0.9
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

def create_materials() :
    # Creates all our materials and returns them as a list.

    def define_tex_coords_common() :
        # creates a node group that defines a common coordinate system
        # for all my image textures.
        tex_coords_common = bpy.data.node_groups.new("SpaceShip.TexCoordsCommon", "ShaderNodeTree")
        ctx = NodeContext(tex_coords_common, (-100, 0))
        tex_coords = ctx.new_node("ShaderNodeTexCoord", ctx.step_across(200))
        group_output = ctx.new_node("NodeGroupOutput", ctx.step_across(200))
        ctx.link(tex_coords.outputs["Object"], group_output.inputs[0])
        group_output.inputs[0].name = tex_coords_common.outputs[0].name = "Coords"
        return tex_coords_common
    #end define_tex_coords_common

    tex_coords_common = define_tex_coords_common()

    def create_texture(ctx, filename, use_alpha, is_color) :
        # Creates an image texture node given filename relative to my
        # “textures” subdirectory. Returns the output terminal to be linked
        # to wherever the texture colour is needed.
        img = load_image(filename, use_alpha, is_color)
        coords = ctx.new_node("ShaderNodeGroup", ctx.step_across(200))
        coords.node_tree = tex_coords_common
        tex = ctx.new_node("ShaderNodeTexImage", ctx.step_across(300))
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
        normal_map = ctx.new_node("ShaderNodeNormalMap", ctx.step_across(200))
        ctx.link(tex_out, normal_map.inputs["Color"])
        normal_map.inputs["Strength"].default_value = 1
        group_output = ctx.new_node("NodeGroupOutput", ctx.step_across(200))
        ctx.link(normal_map.outputs["Normal"], group_output.inputs[0])
        group_output.inputs[0].name = normals_common.outputs[0].name = "Normal"
        deselect_all(normals_common)
        return normals_common
    #end define_normals_common

    normals_common = define_normals_common()

    def set_hull_mat_basics(mat, base_color) :
        # Sets some basic properties for a hull material.
        main_shader = find_main_shader(mat)
        ctx = NodeContext(mat.node_tree, tuple(main_shader.location))
        ctx.step_across(-400)
        ctx.push_pos()
        ctx.step_down(200)
        main_shader.inputs["Base Color"].default_value = base_color
        main_shader.inputs["Specular"].default_value = 0.1
        normal_map = ctx.new_node("ShaderNodeGroup", ctx.step_across(200))
        normal_map.node_tree = normals_common
        ctx.link(normal_map.outputs[0], main_shader.inputs["Normal"])
        ctx.pop_pos()
        deselect_all(mat.node_tree)
        return ctx, main_shader # for adding further nodes if needed
    #end set_hull_mat_basics

    def set_hull_mat_emissive(mat, color, strength) :
        # does common setup for emissive hull materials (windows, engines and other lights)
        main_shader = find_main_shader(mat)
        main_shader.inputs["Emission"].default_value = tuple(c * strength for c in color)
        deselect_all(mat.node_tree)
    #end set_hull_mat_emissive

#begin create_materials

    materials = []
    for material in MATERIAL :
        mat = bpy.data.materials.new(material.name.lower())
        mat.use_nodes = True
        materials.append(mat)
    #end for

    # Choose a base color for the spaceship hull
    hull_base_color = \
      (
            hls_to_rgb
              (
                h = random.random(),
                l = random.uniform(0.05, 0.5),
                s = random.uniform(0, 0.25)
              )
        +
            (1,)
      )

    # Build the hull texture
    set_hull_mat_basics(materials[MATERIAL.HULL], hull_base_color)

    # Build the hull_lights texture
    ctx, main_shader = set_hull_mat_basics(materials[MATERIAL.HULL_LIGHTS], hull_base_color)
      # actually hull_base_color has no effect here, overridden by a node connection below
    # Add a diffuse layer that sets the window color
    ctx.step_down(400)
    ctx.step_across(-1400)
    base_window = create_texture \
      (
        ctx,
        filename = "hull_lights_diffuse.png",
        use_alpha = True,
        is_color = True
      )
    mixer1 = ctx.new_node("ShaderNodeMixRGB", ctx.step_across(200))
    mixer1.blend_type = "ADD"
    mixer1.inputs[0].default_value = 1.0
    save_pos = ctx.pos
    ctx.step_across(200)
    mixer1.inputs[1].default_value = \
      (
            hls_to_rgb
              (
                h = random.random(),
                l = random.uniform(0.5, 1),
                s = random.uniform(0, 0.5)
              )
        +
            (1,)
      )
    ctx.pos = save_pos
    ctx.step_down(200)
    # Add an emissive layer that lights up the windows
    window_light = create_texture \
      (
        ctx,
        filename = "hull_lights_emit.png",
        use_alpha = False,
        is_color = True
      )
    amplifier = ctx.new_node("ShaderNodeMixRGB", ctx.step_across(200))
    amplifier.blend_type = "MULTIPLY"
    amplifier.inputs[0].default_value = 1.0
    ctx.link(window_light, amplifier.inputs[1])
    amplifier.inputs[2].default_value = 3 * (2.0,) + (1,)
    mixer2 = ctx.new_node("ShaderNodeMixRGB", ctx.step_across(200))
    mixer2.blend_type = "ADD"
    mixer2.inputs[0].default_value = 1.0
    ctx.link(base_window, mixer1.inputs[1])
    mixer1.inputs[2].default_value = hull_base_color
    ctx.link(mixer1.outputs[0], mixer2.inputs[1])
    ctx.link(amplifier.outputs[0], mixer2.inputs[2])
    ctx.link(mixer2.outputs[0], main_shader.inputs["Base Color"])
    deselect_all(ctx.graph)

    # Build the hull_dark texture
    set_hull_mat_basics \
      (
        materials[MATERIAL.HULL_DARK],
        tuple(0.3 * x for x in hull_base_color[:3]) + (1,)
      )

    # Choose a glow color for the exhaust + glow discs
    glow_color = hls_to_rgb(h = random.random(), l = random.uniform(0.5, 1), s = 1) + (1,)

    # Build the exhaust_burn texture
    set_hull_mat_emissive(materials[MATERIAL.EXHAUST_BURN], glow_color, 1.0)

    # Build the glow_disc texture
    set_hull_mat_emissive(materials[MATERIAL.GLOW_DISC], glow_color, 1.0)

    return materials
#end create_materials

class parms_defaults :
    "define parameter defaults in a single place for reuse."
    random_seed = ""
    num_hull_segments_min = 3
    num_hull_segments_max = 6
    create_asymmetry_segments = True
    num_asymmetry_segments_min = 1
    num_asymmetry_segments_max = 5
    create_face_detail = True
    allow_horizontal_symmetry = True
    allow_vertical_symmetry = False
    add_bevel_modifier = True
    assign_materials = True
#end parms_defaults

def generate_spaceship(parms) :
    # Generates a textured spaceship mesh and returns the object.
    # Just uses global cube texture coordinates rather than generating UVs.
    # Takes an optional random seed value to generate a specific spaceship.
    # Allows overriding of some parameters that affect generation.
    global random # for use by other routines in this module
    random = Random()
    if parms.random_seed :
        random.seed(parms.random_seed)
    #end if

    # Let's start with a unit BMesh cube scaled randomly
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size = 1)
    scale_vector = Vector \
      (
        (random.uniform(0.75, 2.0), random.uniform(0.75, 2.0), random.uniform(0.75, 2.0))
      )
    bmesh.ops.scale(bm, vec = scale_vector, verts = bm.verts)

    # Extrude out the hull along the X axis, adding some semi-random perturbations
    for face in bm.faces[:] :
        if abs(face.normal.x) > 0.5 :
            hull_segment_length = random.uniform(0.3, 1)
            if parms.num_hull_segments_max >= parms.num_hull_segments_min :
                num_hull_segments = random.randrange \
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
                val = random.random()
                if val > 0.1 :
                    # Most of the time, extrude out the face with some random deviations
                    face = extrude_face(bm, face, hull_segment_length)
                    if random.random() > 0.75 :
                        face = extrude_face \
                          (
                            bm,
                            face,
                            translate_forwards = hull_segment_length * 0.25
                          )
                    #end if

                    # Maybe apply some scaling
                    if random.random() > 0.5 :
                        sy = random.uniform(1.2, 1.5)
                        sz = random.uniform(1.2, 1.5)
                        if is_last_hull_segment or random.random() > 0.5 :
                            sy = 1 / sy
                            sz = 1 / sz
                        scale_face(bm, face, 1, sy, sz)
                    #end if

                    # Maybe apply some sideways translation
                    if random.random() > 0.5 :
                        sideways_translation = Vector \
                          (
                            (0, 0, random.uniform(0.1, 0.4) * scale_vector.z * hull_segment_length)
                          )
                        if random.random() > 0.5 :
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
                    if random.random() > 0.5 :
                        angle = 5 * deg
                        if random.random() > 0.5 :
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
                    rib_scale = random.uniform(0.75, 0.95)
                    face = ribbed_extrude_face \
                      (
                        bm,
                        face,
                        translate_forwards = hull_segment_length,
                        num_ribs = random.randint(2, 4),
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
                    random.random() > 0.85
            ) :
                hull_piece_length = random.uniform(0.1, 0.4)
                for i in \
                    range(random.randrange
                      (
                        parms.num_asymmetry_segments_min,
                        parms.num_asymmetry_segments_max + 1
                      )) \
                :
                    face = extrude_face(bm, face, hull_piece_length)
                    # Maybe apply some scaling
                    if random.random() > 0.25 :
                        s = 1 / random.uniform(1.1, 1.5)
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
            val = random.random()
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
    if parms.allow_horizontal_symmetry and random.random() > 0.5 :
        bmesh.ops.symmetrize(bm, input = bm.verts[:] + bm.edges[:] + bm.faces[:], direction = "Y")
    #end if
    # Apply vertical symmetry sometimes - this can cause spaceship "islands", so disabled by default
    if parms.allow_vertical_symmetry and random.random() > 0.5 :
        bmesh.ops.symmetrize(bm, input = bm.verts[:] + bm.edges[:] + bm.faces[:], direction = "Z")
    #end if

    # Finish up, write the bmesh into a new mesh
    me = bpy.data.meshes.new("Spaceship")
    bm.to_mesh(me)
    bm.free()

    # Add the mesh to the scene
    obj = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(obj)
    # Select and make active
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Recenter the object to its center of mass
    bpy.ops.object.origin_set(type = "ORIGIN_CENTER_OF_MASS")
    ob = bpy.context.object
    ob.location = bpy.context.scene.cursor.location.copy()

    # Add a fairly broad bevel modifier to angularize shape
    if parms.add_bevel_modifier :
        bevel_modifier = ob.modifiers.new("Bevel", "BEVEL")
        bevel_modifier.width = random.uniform(5, 20)
        bevel_modifier.offset_type = "PERCENT"
        bevel_modifier.segments = 2
        bevel_modifier.profile = 0.25
        bevel_modifier.limit_method = "NONE"
    #end if

    # Add materials to the spaceship
    me = ob.data
    materials = create_materials()
    for mat in materials :
        if parms.assign_materials :
            me.materials.append(mat)
        else :
            me.materials.append(bpy.data.materials.new(name = "Material"))
        #end if
    #end for

    return obj
#end generate_spaceship

if __name__ == "__main__" :

    import datetime

    # Deletes all existing spaceships and unused materials from the scene
    def reset_scene() :
        for item in bpy.data.objects :
            item.select = item.name.startswith("Spaceship")
        #end for
        bpy.ops.object.delete()
        for material in bpy.data.materials :
            if not material.users :
                bpy.data.materials.remove(material)
            #end if
        #end for
        for texture in bpy.data.textures :
            if not texture.users :
                bpy.data.textures.remove(texture)
            #end if
        #end for
    #end reset_scene

    # When true, this script will generate a single spaceship in the scene.
    # When false, this script will render multiple movie frames showcasing lots of ships.
    generate_single_spaceship = True

    if generate_single_spaceship :
        # Reset the scene, generate a single spaceship and focus on it
        reset_scene()
        parms_defaults.random_seed = "" # add anything here to generate the same spaceship
        obj = generate_spaceship(parms_defaults)

        # View the selected object in all views
        for area in bpy.context.screen.areas :
            if area.type == "VIEW_3D" :
                ctx = bpy.context.copy()
                ctx["area"] = area
                ctx["region"] = area.regions[-1]
                bpy.ops.view3d.view_selected(ctx)
            #end if
        #end for

    else :
        # Export a movie showcasing many different kinds of ships

        # Settings
        output_path = "" # leave empty to use script folder
        total_movie_duration = 16
        total_spaceship_duration = 1
        yaw_rate = 45 * deg # angle/sec
        yaw_offset = 220 * deg # angle/sec
        camera_pole_rate = 1
        camera_pole_pitch_min = 15 * deg
        camera_pole_pitch_max = 30 * deg
        camera_pole_pitch_offset = 0 * deg
        camera_pole_length = 10
        camera_refocus_object_every_frame = False
        fov = 60 * deg
        fps = 30
        res_x = 1920
        res_y = 1080

        # Batch render the movie frames
        inv_fps = 1 / fps
        movie_duration = 0
        spaceship_duration = total_spaceship_duration
        scene = bpy.data.scenes["Scene"]
        scene.render.resolution_x = res_x
        scene.render.resolution_y = res_y
        scene.camera.rotation_mode = "XYZ"
        scene.camera.data.angle = fov
        frame = 0
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        while movie_duration < total_movie_duration :
            movie_duration += inv_fps
            spaceship_duration += inv_fps
            if spaceship_duration >= total_spaceship_duration :
                spaceship_duration -= total_spaceship_duration

                # Generate a new spaceship
                reset_scene()
                obj = generate_spaceship(parms_defaults)

                # look for a mirror plane in the scene, and position it
                # just underneath the ship if found
                lowest_z = centre = min((Vector(b).z for b in obj.bound_box))
                plane_obj = bpy.data.objects.get("Plane")
                if plane_obj :
                    plane_obj.location.z = lowest_z - 0.3
                #end if
            #end if

            # Position and orient the camera
            yaw = yaw_offset + yaw_rate * movie_duration
            camera_pole_pitch_lerp = 0.5 * (1 + math.cos(camera_pole_rate * movie_duration)) # 0-1
            camera_pole_pitch = \
              (
                    camera_pole_pitch_max * camera_pole_pitch_lerp
                +
                    camera_pole_pitch_min * (1 - camera_pole_pitch_lerp)
              )
            scene.camera.rotation_euler = \
                (
                    90 * deg - camera_pole_pitch + camera_pole_pitch_offset,
                    0,
                    yaw
                )
            scene.camera.location = \
                (
                    math.sin(yaw) * camera_pole_length,
                    math.cos(yaw) * -camera_pole_length,
                    math.sin(camera_pole_pitch) * camera_pole_length
                )
            if camera_refocus_object_every_frame :
                bpy.ops.view3d.camera_to_view_selected()
            #end if

            # Render the scene to disk
            script_path = bpy.context.space_data.text.filepath if bpy.context.space_data else __file__
            folder = output_path if output_path else os.path.split(os.path.realpath(script_path))[0]
            filename = os.path.join \
              (
                "renders",
                timestamp,
                timestamp + "_" + str(frame).zfill(5) + ".png"
              )
            bpy.data.scenes["Scene"].render.filepath = os.path.join(folder, filename)
            print("Rendering frame " + str(frame) + "...")
            bpy.ops.render.render(write_still = True)
            frame += 1
        #end while movie_duration < total_movie_duration

    #end if generate_single_spaceship

#end if __name__ == "__main__"
