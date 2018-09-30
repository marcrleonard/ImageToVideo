import sys
import datetime
from subprocess import Popen, PIPE

from PIL import Image as PImage
from PIL import ImageChops as PImageChops

# from pyvips import Image as VImage

import threading
import os
import io
import numpy as np
import cv2
import subprocess
import shutil
import time
import gc


# from gi.repository import Vips


class ImageAnimation(object):
    def __init__(self, original_image, output_raster_width, output_raster_height, total_seconds, fps, image_lib='cv'):
        self.file_path = original_image
        self.image_lib = None

        self.output_raster_width = output_raster_width
        self.output_raster_height = output_raster_height
        self.total_frames = int(float(total_seconds) * float(fps))

        self.image_lib = image_lib

        self.fps = fps

        if self.image_lib == 'pillow':
            print('using Pillow')
            self.original_image = PImage.open(self.file_path)
            self.original_image_width, self.original_image_height = self.original_image.size

        # if self.image_lib == 'vips':
        #     print('using vips')
        #     self.original_image = VImage.new_from_file(self.file_path)
        #     self.original_image_width = self.original_image.width
        #     self.original_image_height = self.original_image.height

        self.output_file_name = 'output'

        if self.image_lib == 'cv':
            print('using cv')
            self.original_image = cv2.imread(
                self.file_path, cv2.IMREAD_UNCHANGED)
            self.original_image_height, self.original_image_width, _ = self.original_image.shape

        self.processed_frames = 0
        self.render_start_time = 0
        self.render_status = 'queued'
        self.render_estimated_seconds_remaining = 0
        self.render_estimated_total_seconds = 0
        self.render_fps = 0

        self.prores_mez = False

        self.ffmpeg = shutil.which('ffmpeg')
        if not self.ffmpeg:
            self.ffmpeg = '/usr/local/bin/ffmpeg'

        self.convert = shutil.which('convert')

        if not self.convert:
            self.convert = '/usr/local/bin/convert'

        self.water_mark = False

    def render_status_update(self):
        self.processed_frames = self.processed_frames + 1.0
        clock_time = datetime.datetime.utcnow() - self.render_start_time
        self.render_fps = round(
            (float(self.processed_frames) / clock_time.total_seconds()), 2)
        self.render_estimated_total_seconds = float(
            1 / self.percent_complete()) * clock_time.total_seconds()
        self.render_estimated_seconds_remaining = datetime.timedelta(
            seconds=(int(self.render_estimated_total_seconds - clock_time.total_seconds())))

    def percent_complete(self):
        return self.processed_frames / self.total_frames

    def Render(self):

        self.render_status = 'starting'

        self.render_start_time = datetime.datetime.utcnow()

        p = Popen([self.ffmpeg,
                   '-loglevel', 'panic',
                   '-s', '{}x{}'.format(self.output_raster_width, self.output_raster_height),
                   '-pix_fmt', 'yuvj420p',
                   '-y',
                   '-f', 'image2pipe',
                   '-vcodec', 'mjpeg',
                   '-r', str(self.fps),
                   '-i', '-',
                   '-r', str(self.fps),
                   '-f', 'mp4',
                   '-vcodec', 'libx264',
                   '-preset', 'fast',
                   # '-crf', '26',
                   self.output_file_name + '.mp4'], stdin=PIPE)

        if self.prores_mez:
            p_prores = Popen([self.ffmpeg,
                              '-loglevel', 'panic',
                              '-s', '1920x1080',
                              '-pix_fmt', 'yuvj420p',
                              '-y',
                              '-f', 'image2pipe',
                              '-vcodec', 'mjpeg',
                              '-r', self.fps,
                              '-i', '-',
                              '-r', self.fps,
                              '-f', 'mov',
                              '-vcodec', 'prores',
                              '-profile:v', '3',
                              '-aspect', '16:9', '-y',
                              self.output_file_name + '.mov'], stdin=PIPE)

        self.render_status = 'rendering'

        for frame in range(self.total_frames):

            gc.collect()

            begin_scale = 1
            diff_increments_zoom = 0

            zoom = begin_scale - (diff_increments_zoom * frame)

            y_total = 0

            # at 1 zoom, it's (5184 - 1920) / 79 frames...  41 pixels
            # at .45 zoom, it's ((5184 *.45) - 1920) / 79 frames...  5 pixels (413/79 total)

            resize_width = int(self.original_image_width * zoom)
            resize_height = int(self.original_image_height * zoom)

            # if self.image_lib == 'vips':
            #
            #     # image_resize = VImage.thumbnail(self.file_path, resize_height)
            #     # image_resize.copy(xoffset=int(x_total), yoffset=int(y_total))
            #     # # if x_total < 0:
            #     # #     x_total = x_total * -1
            #     # # if y_total < 0:
            #     # #     y_total = y_total * -1
            #     # #
            #     # # print(x_total)
            #     # # print(y_total)
            #     #
            #     # # output = image_resize.crop(int(x_total), int(y_total), (self.output_raster_width + int(x_total)), (self.output_raster_height + int(y_total)))
            #     # output = image_resize.crop(0, 0, (self.output_raster_width), (self.output_raster_height))
            #     # data = output.write_to_buffer('.JPEG', Q=95)
            #     # image_bytes = PImage.open(io.BytesIO(data))
            #     # image_bytes.save(p.stdin, 'JPEG')
            #
            #
            #     image_resize = VImage.thumbnail(self.file_path, (zoom * self.original_image_width))
            #     image_resize.copy(xoffset=int(x_total), yoffset=int(y_total))
            #     output = image_resize.crop(0, 0, self.output_raster_width, self.output_raster_height)
            #     data = output.write_to_buffer('.JPEG', Q=95)
            #     image_bytes = PImage.open(io.BytesIO(data))
            #     image_bytes.save(p.stdin, 'JPEG')

            if self.image_lib == 'pillow':
                image_resize = self.original_image.resize(
                    (resize_width, resize_height), resample=PImage.BICUBIC)
                image_offset = PImageChops.offset(
                    image_resize, xoffset=int(x_total), yoffset=int(y_total))
                image = image_offset.crop(
                    (0, 0, self.output_raster_width, self.output_raster_height))

                image.save(p.stdin, 'JPEG')
                # image.save(p_prores.stdin, 'JPEG')

            if self.image_lib == 'cv':
                x_total = 0

                # adds zoom
                image_resize = cv2.resize(self.original_image, (0, 0), fx=zoom, fy=zoom)

                #
                M = np.float32([[1, 0, x_total], [0, 1, y_total]])

                image_offset = cv2.warpAffine(image_resize, M,
                                              (self.original_image_width, self.original_image_height))

                image = image_offset[0:self.output_raster_height, 0:self.output_raster_width].copy()

                corrected_img = cv2.cvtColor(image_offset, cv2.COLOR_BGR2RGB)

                from_pil = PImage.fromarray(corrected_img)

                from_pil.save(p.stdin, 'JPEG')

                # from_pil.show()

                if self.prores_mez:
                    from_pil.save(p_prores.stdin, 'JPEG')

            self.render_status_update()

            # https://stackoverflow.com/questions/13294919/can-you-stream-images-to-ffmpeg-to-construct-a-video-instead-of-saving-them-t
            # For anyone who stumbles upon this in the future, replacing 'mjpeg' with 'png' and 'JPEG' with 'PNG' worked for me to use png.
            # python 3.6 https://stackoverflow.com/questions/40108816/python-running-as-windows-service-oserror-winerror-6-the-handle-is-invalid

        p.stdin.close()
        p.wait()

        gc.collect()

        self.time_end = datetime.datetime.utcnow()
        seconds_delta = (self.time_end-self.render_start_time).total_seconds()
        print('{} minutes'.format(seconds_delta / 60))
        self.render_status = 'done'


if __name__ == '__main__':

    if len(sys.argv) > 1:
        original_image = sys.argv[1]
    else:
        # original_image = "IMG_0015.jpg"
        original_image = "test_image.jpg"

    image_video = ImageAnimation(original_image, 1920, 1080, 2, 24)

    render_thread = threading.Thread(target=image_video.Render)
    render_thread.start()

    percentage_complete = image_video.percent_complete()
    render_status = image_video.render_status
    prev_percentage = 0
    while render_status != 'done':
        prev_percentage = percentage_complete
        percentage_complete = int(image_video.percent_complete() * 100)
        render_status = image_video.render_status
        if percentage_complete != prev_percentage:
            print('{}% {}fps {} Remaining'.format(percentage_complete,
                                                  image_video.render_fps, image_video.render_estimated_seconds_remaining))
        time.sleep(.2)

    sys.exit(1)
