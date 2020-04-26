#!/usr/bin/python3
#+
# Generate an addon release archive.
#-

import os.path
import zipfile

SRC_DIR = os.path.dirname(os.path.abspath(__file__))

basename = "add_mesh_SpaceshipGenerator"
outfilename = "%s.zip" % basename
out = zipfile.ZipFile(outfilename, "w", zipfile.ZIP_DEFLATED)
for filename in \
    (
        "__init__.py",
        "spaceship_generator.py",
        "textures/hull_normal.png",
        "textures/hull_lights_emit.png",
        "textures/hull_lights_diffuse.png",
        "icons/spaceship.png",
    ) \
:
    out.write(os.path.join(SRC_DIR, filename), "/".join((basename, filename)))
#end for
out.close()

print("created file: %s" % outfilename)
