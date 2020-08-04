# Spaceship Generator

A Blender script to procedurally generate 3D spaceships from a random seed.

![Spaceship screenshots](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/spaceships_grid.jpg)

Usage
-----
* Install Blender 2.82 or greater: http://blender.org/download/
* Download newest `add_mesh_SpaceshipGenerator.zip` from the [Releases](https://github.com/ldo/blender_spaceship_generator/releases) section
* Under File > User Preferences... > Add-ons > Install From File... open the downloaded ZIP file
* Under File > User Preferences... > Add-ons enable this script (search for "spaceship")
* Add a spaceship in the 3D View under Add > Mesh > Spaceship

How it works
------------

![Step-by-step animation](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/step-by-step-animation.gif)

Watch on YouTube: https://www.youtube.com/watch?v=xJZyXqJ6nog

* Start with a box.
* Build the hull: Extrude the front/rear faces several times, adding random translation/scaling/rotation along the way.
* Add asymmetry to the hull: Pick random faces and extrude them out in a similar manner, reducing in scale each time.
* Add detail to the hull: Categorize each face by its orientation and generate details on it such as engines, antenna, weapon turrets, lights etc.
* Sometimes apply horizontal symmetry.
* Add a Bevel modifier to angularize the shape a bit.
* Apply materials to the final result.
* Take over the universe with your new infinite fleet of spaceships.

Extreme examples
----------------
The following screenshots were created using extreme values for the number of hull segments and asymmetry segments to show how the algorithm works.

![Extreme spaceship screenshots](https://raw.githubusercontent.com/a1studmuffin/SpaceshipGenerator/master/screenshots/extreme_examples.jpg)

Tips and Tricks
---------------
* The seeds used for generating random geometry and materials default to random integers,
but you can replace these with any string. Different seeds are chosen every time you create
a new spaceship, but they do not change when you edit the parameters for regenerating the
current spaceship (unless you change them).
* Materials are generated with heavy use of node groups, to allow easy customization.
For example, all colours are derived from a common colour-scheme node group, so changes
made here can affect all relevant materials for a single spaceship at once. The node groups
work across both Eevee and Cycles renderers.
* You can go further, and replace the textures with your own ones. `hull_normal.png` is a
normal map that adds extra surface detail “greebles”. `hull_lights_emit.png` defines the positions
of the windows; it is used as an emissive texture to make them glow.

Credits
-------
Written for fun as part of the [/r/proceduralgeneration](https://www.reddit.com/r/proceduralgeneration/) June 2016 [monthly challenge](https://www.reddit.com/r/proceduralgeneration/comments/4mn9gj/monthly_challenge_7_june_2016_procedural/).

Released under the [MIT License].

Originally authored by Michael Davies, this version adapted by Lawrence D’Oliveiro.

> GitHub [@a1studmuffin](https://github.com/a1studmuffin)
> Twitter [@butterparty](https://twitter.com/butterparty)

Special thanks to [@panzi](https://github.com/panzi) for bugfixes, a proper GUI and build script. Also to [@mjrthemes](https://github.com/mjrthemes) for bugfixing.

[MIT License]: http://mit-license.org/
