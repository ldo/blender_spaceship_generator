bl_info = \
    {
        "name" : "Spaceship Generator",
        "author" : "Michael Davies, Lawrence D'Oliveiro",
        "version" : (1, 6, 5),
        "blender" : (3, 0, 0),
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

import random
import bpy
import bpy.utils.previews
import bpy.props

class GenerateSpaceship(bpy.types.Operator) :
    "Procedurally generate 3D spaceships from a random seed."
    bl_idname = "add_mesh.generate_spaceship"
    bl_label = "Spaceship"
    bl_options = {"REGISTER", "UNDO"}

    df = spaceship_generator.parms_defaults # temp short name
    ALIGN_TO = spaceship_generator.ALIGN_TO
    geom_ranseed : bpy.props.StringProperty \
      (
        default = df.geom_ranseed,
        name = "Geometry Seed"
      )
    align : bpy.props.EnumProperty \
      (
        default = df.align,
        items =
            (
                (ALIGN_TO.NONE.idstr, "Nothing", "leave as created"),
                (ALIGN_TO.WORLD.idstr, "World", "align forward to negative-y direction"),
                (ALIGN_TO.VIEW.idstr, "View", "align forward to view"),
                (ALIGN_TO.CURSOR.idstr, "3D Cursor", "take rotation from 3D cursor"),
            ),
        name = "Align"
      )
    num_hull_segments_min : bpy.props.IntProperty \
      (
        default = df.num_hull_segments_min,
        min = 0,
        soft_max = 16,
        name = "Min. Hull Segments"
      )
    num_hull_segments_max : bpy.props.IntProperty \
      (
        default = df.num_hull_segments_max,
        min = 0,
        soft_max = 16,
        name = "Max. Hull Segments"
      )
    create_asymmetry_segments : bpy.props.BoolProperty \
      (
        default = df.create_asymmetry_segments,
        name = "Create Asymmetry Segments"
      )
    num_asymmetry_segments_min : bpy.props.IntProperty \
      (
        default = df.num_asymmetry_segments_min,
        min = 1,
        soft_max = 16,
        name = "Min. Asymmetry Segments"
      )
    num_asymmetry_segments_max : bpy.props.IntProperty \
      (
        default = df.num_asymmetry_segments_max,
        min = 1,
        soft_max = 16,
        name = "Max. Asymmetry Segments"
      )
    create_face_detail : bpy.props.BoolProperty \
      (
        default = df.create_face_detail,
        name = "Create Face Detail"
      )
    allow_horizontal_symmetry : bpy.props.BoolProperty \
      (
        default = df.allow_horizontal_symmetry,
        name = "Allow Horizontal Symmetry"
      )
    allow_vertical_symmetry : bpy.props.BoolProperty \
      (
        default = df.allow_vertical_symmetry,
        name = "Allow Vertical Symmetry"
      )
    add_bevel_modifier : bpy.props.BoolProperty \
      (
        default = df.add_bevel_modifier,
        name = "Add Bevel Modifier"
      )
    create_materials : bpy.props.BoolProperty \
      (
        default = df.create_materials,
        name = "Assign Materials"
      )
    show_materials_details : bpy.props.BoolProperty \
      (
        default = False,
        name = "Show Materials Details"
      )
    hull_base_colour : bpy.props.FloatVectorProperty \
      (
        subtype = "COLOR",
        default = df.hull_base_colour,
        name = "Hull Base Colour"
      )
    hull_darken : bpy.props.FloatProperty \
      (
        default = df.hull_darken,
        min = 0,
        max = 1,
        name = "Hull Darken Factor"
      )
    hull_emissive_colour : bpy.props.FloatVectorProperty \
      (
        subtype = "COLOR",
        default = df.hull_emissive_colour,
        name = "Window Emissive Colour"
      )
    glow_colour : bpy.props.FloatVectorProperty \
      (
        subtype = "COLOR",
        default = df.glow_colour,
        name = "Engine/Disc Glow Colour"
      )
    grunge_factor : bpy.props.FloatProperty \
      (
        default = df.grunge_factor,
        min = 0,
        max = 1,
        name = "Material Grunge"
      )
    del df, ALIGN_TO

    def draw(self, context) :
        main = self.layout
        main.prop(self, "geom_ranseed", text = "Seed")
        main.prop(self, "align", text = "Align To")
        sub = main.box()
        sub.label(text = "Hull Segments")
        row = sub.row()
        row.prop(self, "num_hull_segments_min", text = "Min")
        row.prop(self, "num_hull_segments_max", text = "Max")
        if self.create_asymmetry_segments :
            sub = main.box()
            sub.prop(self, "create_asymmetry_segments", text = "Create Asymmetry Segments")
            row = sub.row()
            row.prop(self, "num_asymmetry_segments_min", text = "Min")
            row.prop(self, "num_asymmetry_segments_max", text = "Max")
        else :
            main.prop(self, "create_asymmetry_segments", text = "Create Asymmetry Segments")
        #end if
        main.prop(self, "create_face_detail", text = "Create Face Detail")
        sub = main.box()
        sub.label(text = "Allow Symmetry")
        row = sub.row()
        row.prop(self, "allow_horizontal_symmetry", text = "Horizontal")
        row.prop(self, "allow_vertical_symmetry", text = "Vertical")
        main.prop(self, "add_bevel_modifier", text = "Add Bevel Modifier")
        if self.create_materials :
            sub = main.box()
            row = sub.row()
            row.prop(self, "create_materials", text = "Create Materials")
            row.prop(self, "show_materials_details", text = "Show Details")
            if self.show_materials_details :
                sub.prop(self, "hull_base_colour", text = "Hull Base")
                sub.prop(self, "hull_darken", text = "Hull Darken")
                sub.prop(self, "hull_emissive_colour", text = "Hull Emissive")
                sub.prop(self, "glow_colour", text = "Engine/Disc Glow")
                sub.prop(self, "grunge_factor", text = "Grunge")
            #end if
        else :
            row = main.row()
            row.prop(self, "create_materials", text = "Create Materials")
            row.prop(self, "show_materials_details", text = "Show Details")
        #end if
    #end draw

    def invoke(self, context, event) :
        maxseed = 1e6
          # [0 .. 999999] is enough to be interesting by
          # default. Users can always replace seeds with
          # anything they like.
        self.geom_ranseed = str(random.randrange(maxseed))
        spaceship_generator.randomize_colours(self, random.Random())
        spaceship_generator.generate_spaceship(self)
        return {"FINISHED"}
    #end invoke

    def execute(self, context) :
        spaceship_generator.generate_spaceship(self)
        return {"FINISHED"}
    #end execute

#end GenerateSpaceship

_classes_ = \
    (
        GenerateSpaceship,
    )

icons = None

def menu_func(self, context) :
    self.layout.operator \
      (
        GenerateSpaceship.bl_idname,
        text = "Spaceship",
        icon_value = icons["spaceship"].icon_id
      )
#end menu_func

def register() :
    global icons
    if icons == None :
        icons = bpy.utils.previews.new()
        icons.load \
          (
            "spaceship",
            spaceship_generator.resource_path("icons", "spaceship.png"),
            "IMAGE"
          )
    #end if
    for ċlass in _classes_ :
        bpy.utils.register_class(ċlass)
    #end for
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
#end register

def unregister() :
    global icons
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    for ċlass in _classes_ :
        bpy.utils.unregister_class(ċlass)
    #end for
    if icons != None :
        bpy.utils.previews.remove(icons)
        icons = None
    #end if
#end unregister

if __name__ == "__main__" :
    register()
#end if
