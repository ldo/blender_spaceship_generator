bl_info = \
    {
        "name" : "Spaceship Generator",
        "author" : "Michael Davies",
        "version" : (1, 1, 5),
        "blender" : (2, 79, 0),
        "location" : "View3D > Add > Mesh",
        "description" : "Procedurally generate 3D spaceships from a random seed.",
        "wiki_url" : "https://github.com/a1studmuffin/SpaceshipGenerator/blob/master/README.md",
        "tracker_url" : "https://github.com/a1studmuffin/SpaceshipGenerator/issues",
        "category" : "Add Mesh",
    }

if "bpy" in locals() :
    # reload logic (magic)
    import importlib
    importlib.reload(spaceship_generator)
else :
    from . import spaceship_generator
#end if

import bpy
from bpy.props import \
    BoolProperty, \
    IntProperty, \
    StringProperty

class GenerateSpaceship(bpy.types.Operator) :
    "Procedurally generate 3D spaceships from a random seed."
    bl_idname = "mesh.generate_spaceship"
    bl_label = "Spaceship"
    bl_options = {"REGISTER", "UNDO"}

    df = spaceship_generator.parms_defaults # temp short name
    random_seed = StringProperty \
      (
        default = df.random_seed,
        name = "Seed"
      )
    num_hull_segments_min = IntProperty \
      (
        default = df.num_hull_segments_min,
        min = 0,
        soft_max = 16,
        name = "Min. Hull Segments"
      )
    num_hull_segments_max = IntProperty \
      (
        default = df.num_hull_segments_max,
        min = 0,
        soft_max = 16,
        name = "Max. Hull Segments"
      )
    create_asymmetry_segments = BoolProperty \
      (
        default = df.create_asymmetry_segments,
        name = "Create Asymmetry Segments"
      )
    num_asymmetry_segments_min = IntProperty \
      (
        default = df.num_asymmetry_segments_min,
        min = 1,
        soft_max = 16,
        name = "Min. Asymmetry Segments"
      )
    num_asymmetry_segments_max = IntProperty \
      (
        default = df.num_asymmetry_segments_max,
        min = 1,
        soft_max = 16,
        name = "Max. Asymmetry Segments"
      )
    create_face_detail = BoolProperty \
      (
        default = df.create_face_detail,
        name = "Create Face Detail"
      )
    allow_horizontal_symmetry = BoolProperty \
      (
        default = df.allow_horizontal_symmetry,
        name = "Allow Horizontal Symmetry"
      )
    allow_vertical_symmetry = BoolProperty \
      (
        default = df.allow_vertical_symmetry,
        name="Allow Vertical Symmetry"
      )
    add_bevel_modifier = BoolProperty \
      (
        default = df.add_bevel_modifier,
        name = "Add Bevel Modifier"
      )
    assign_materials = BoolProperty \
      (
        default = df.assign_materials,
        name = "Assign Materials"
      )
    del df

    def execute(self, context) :
        spaceship_generator.generate_spaceship(self)
        return {"FINISHED"}
    #end execute

#end GenerateSpaceship

_classes_ = \
    (
        GenerateSpaceship,
    )

def menu_func(self, context) :
    self.layout.operator(GenerateSpaceship.bl_idname, text = "Spaceship")
#end menu_func

def register() :
    for ċlass in _classes_ :
        bpy.utils.register_class(ċlass)
    #end for
    bpy.types.INFO_MT_mesh_add.append(menu_func)
#end register

def unregister() :
    bpy.types.INFO_MT_mesh_add.remove(menu_func)
    for ċlass in _classes_ :
        bpy.utils.unregister_class(ċlass)
    #end for
#end unregister

if __name__ == "__main__" :
    register()
#end if
