ImageToVideo
-------------------------

This module enables a simple way to make an image into a video.

Under the hood
=============================

ImageToVideo uses OpenCV/Numpy as a 'middle man'. It handles any zoom, resize, rotate functions (and eventually will power the plugin extensibility). All encoding is done via FFMPEG.
In the future, I will be adding other imaging libraries. I have preliminary versions of using Pillow and Pyvips

Example

=============================


.. code-block:: python

    video_to_convert = ImageAnimation(original_image, # image path
                                      1920,           # video width
                                      1080,           # video height
                                      2,              # movie length
                                      24,             # framerate
                                      image_lib='cv'  # image library
                                      )
    video_to_convert.Render()




TODO
=============================

- Image sequence support
- Create a logical payload to be passed into the class to define the conversion. Or, maybe it should be advised to set attributes.
- Add other options to encode output. Or possible add presets
- Make it extensible to allow for animations, or any other 'plugins' ie... watermarks, text, etc...
