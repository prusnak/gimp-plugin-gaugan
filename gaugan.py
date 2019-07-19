#!/usr/bin/env python2
from gimpfu import register, main, gimp, RGB_IMAGE, NORMAL_MODE, pdb
import os, tempfile

import base64
from io import BytesIO
from datetime import datetime
from random import choice, randint
from time import time
import urllib, urllib2

API = [
    "http://34.221.104.254:443/",
    "http://34.220.80.140:443/",
    "http://54.212.242.58:443/",
]
ORIGIN = "http://34.220.80.140"
REFERER = "http://34.220.80.140/gaugan/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"


class Multipart:
    def __init__(self):
        self.boundary = "-" * 27
        self.boundary += "".join([choice("0123456789") for _ in range(29)])
        self.res = []

    def add(self, key, value):
        self.res.append("--" + self.boundary)
        self.res.append('Content-Disposition: form-data; name="%s"' % key)
        self.res.append("")
        self.res.append(value)

    def result(self):
        res = self.res + ["--" + self.boundary + "--", ""]
        return "\r\n".join(res)


class GauganAPI:
    def __init__(self):
        self.api = choice(API)
        self.uuid = "%s,%s-%s" % (
            datetime.today().strftime("%-m/%d/%Y"),
            int(time() * 1000),
            randint(0, 1000000000),
        )

    def __request(self, method, data={}, multipart=False):
        data["name"] = self.uuid
        if multipart:
            m = Multipart()
            for k, v in data.items():
                m.add(k, v)
            payload = m.result()
        else:
            payload = urllib.urlencode(data)
        request = urllib2.Request(self.api + method, payload)
        request.add_header("Referer", REFERER)
        request.add_header("Origin", ORIGIN)
        request.add_header("User-Agent", UA)
        if multipart:
            request.add_header("Content-Type", "multipart/form-data; boundary=" + m.boundary)
        else:
            request.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
        response = urllib2.urlopen(request)
        return response.read()

    def convert(self, image, style="random"):
        self.__request(
            "nvidia_gaugan_submit_map",
            data={
                "imageBase64": "data:image/png;base64," + base64.b64encode(image).decode()
            },
        )
        return self.__request(
            "nvidia_gaugan_receive_image",
            data={"style_name": style, "artistic_style_name": "none"},
            multipart=True,
        )


def python_gaugan(img, layer):
    if not layer.is_rgb:
        raise ValueError("Expected RGB layer")
    # because pdb cannot save to a buffer, we have to use a temporary file instead
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    pdb.file_png_save(img, layer, f.name, f.name, 0, 9, 0, 0, 0, 0, 0)
    data = open(f.name, "rb").read()
    os.unlink(f.name)
    # send to Gaugan API
    gaugan = GauganAPI()
    jpg = gaugan.convert(data)
    # save result to a temporary file, because pdb cannot load from a buffer
    f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    open(f.name, "wb").write(jpg)
    # open the temp file
    image = pdb.gimp_file_load(f.name, f.name)
    # copy the first layer to clipboard
    pdb.gimp_edit_copy(image.layers[0])
    os.unlink(f.name)
    # paste clipboard contents as a floating selection
    floating = pdb.gimp_edit_paste(layer, 0)
    floating.name = layer.name + " [Gaugan]"

register(
    "python_fu_gaugan",
    "Process the selected layer in GauGAN",
    "Process the selected layer in GauGAN",
    "Pavol Rusnak <pavol@rusnak.io>",
    "MIT License",
    "2019",
    "<Image>/Filters/GauGAN...",
    "RGB*",
    [],
    [],
    python_gaugan)

main()