#+
# Demo script that can generate a single spaceship, or a movie
# comprising multiple spaceships. Enable the add_mesh_SpaceshipGenerator
# addon, open/copy this script in/into Blender’s Text Editor, and
# press ALT-P to run it.
#-

import bpy
from add_mesh_SpaceshipGenerator.spaceship_generator import \
    deg, \
    parms_defaults, \
    generate_spaceship

# When true, this script will generate a single spaceship in the scene.
# When false, this script will render multiple movie frames showcasing lots of ships.
generate_single_spaceship = True

import os
import math
import datetime
import bpy
from mathutils import \
    Vector

# Deletes all existing spaceships and unused materials from the scene
def reset_scene() :
    for item in bpy.data.objects :
        item.select_set(item.name.startswith("Spaceship"))
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

class parms(parms_defaults) :
    geom_ranseed = ""
    mat_ranseed = ""
      # add anything here to generate the same spaceship
#end class

if generate_single_spaceship :
    # Reset the scene, generate a single spaceship and focus on it
    reset_scene()
    obj = generate_spaceship(parms)

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
            obj = generate_spaceship(parms)

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
