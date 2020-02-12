Jupyter MicroPython Remote Kernel
=================================

Jupyter kernel to interact with a MicroPython board over its REPL
interface.

Typically used with micropython boards over the USB / Serial interface,
however it should also work through the WEBREPL (available on ESP8266
only). Also includes a few advanced features for micorpython project
management; running mpy-cross, uploading files, syncing local libs to micropython etc.

Micropython
-----------
This kernel requires support in micropython from https://github.com/micropython/micropython/pull/3836
At the time of publishing, this is not in the current release, 1.9.4, so will require a master / daily snapshot until 1.9.5

Installation
------------

Ensure you have a new enough micropython installed on your board (see above).

You also need python 3.6 or above, ensuring it’s available from your current
command line. Optionally (recommended) use your favourite pipenv / virtualenv to set
up a clean environment to run jupyter from.

Then install this module:

::

   pip install jupyter_micropython_remote

Install the kernel into jupyter itself using the shell command:

::

   python -m mpy_kernel.install

This registers the kernel with Jupyter so it can be selected for use in
notebooks

Running
-------

Now run Jupyter notebooks:

::

   jupyter notebook

In the notebook click the New notebook button in the upper right, you
should see your MicroPython kernel display name listed.

The first cell will need to be something like:

::

   %connect <device> --baudrate=115200 --user='micro' --password='python' --wait=0

eg:

::

   %connect "USB-SERIAL CH340""

or something that matches the serial port that you connect to your
MicroPython/ESP8266 with.

The ``<device>`` and args matches the command used to run the standard
``pyboard.py``:

::

   device can be serial port device or name

   device can start with "exec:"
      "Execute a process and emulate serial connection using its stdin/stdout."

   device can start with "execpty:"
       Execute a process which creates a PTY and prints slave PTY as
       first line of its output, and emulate serial connection using
       this PTY

   device can be an ip address for webrepl communication

You should now be able to execute MicroPython commands by running the
cells.

There is a micropythondemo.ipynb file in the directory you could look at
with some of the features shown.

If a cell is taking too long to interrupt, it may respond to a “Kernel”
-> “Interrupt” command.

Alternatively hit Escape and then ‘i’ twice.

To do a soft reboot (when you need to clear out the modules and recover
some memory) type:

::

   %reboot

| Note: Restarting the kernel does not actually reboot the device.
| Also, pressing the reset button will probably mess things up, because
  this interface relies on the ctrl-A non-echoing paste mode to do its
  stuff.

You can list all the functions with:

::

   %lsmagic

mprepl
-------

The communications interface to the micropython module is based on mprepl and pyboard.
mprepl was originally sourced from https://github.com/micropython/micropython/pull/3034

This module utilises the virtual filesystem within micropython ( > 1.9.4 required )
to mount the local pc's working directory jupyter was run from in the actual micropython
environment at the directory ``/remote/``

This allows you to view, open, read, write and copy files to and from micropython to your pc with
ease.

::

   import os
   print(os.listdir("/remote/")

There is also an injected ``Util`` class with some extra file handling tools,
culminating with a ``sync(source, target, delete=True, include=None, exclude=None)``
which will copy all files/folders from source to target, optionally with include or exclude
regex filters.

::

   Util.sync("/remote/src", "/lib/", delete=True, include=".*\.mpy")

See the file ``mpy_kernel/mprepl_utils.py`` for more details

%local
------
Individual cells can also be run on the local pc instead of the remote
kernel by starting a cell with ``%local``

This can be useful to work directly with local files, use ipywidgets, etc.
Commands here will be run by the standard ipython kernel.

In `%local` cells, a special global function ``remote()`` is also available which
will pass a single string argument to the micropython board to be run, returning
any stdout from the command. Eg:

micropython cell

::

   from machine import Pin
   import neopixel
   pixels = neopixel.NeoPixel(Pin(4, Pin.OUT), 1)

   def set_colour(r, g, b):
       pixels[0] = (r, g, b)
       pixels.write()

   set_colour(0xff, 0xff, 0xff)

local cell

::

   %local
   import colorsys
   from ipywidgets import interact, Layout, FloatSlider

   def set_hue(hue):
       r, g, b = (int(p*255) for p in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
       remote(f"set_colour({r}, {g}, {b})")

   slider = FloatSlider(min=0,max=1.0,step=0.01, layout=Layout(width='80%', height='80px'))
   interact(set_hue, hue=slider)

Contributing
------------

Please use and improve this kernel any way you see fit!

I'd prefer pull requests against the main repo: https://gitlab.com/alelec/jupyter_micropython_remote
I'll happily review and accept anything on the legacy github if you are aren't already on gitlab: https://github.com/andrewleech/jupyter_micropython_remote


Background
----------

This Jupyter MicroPython Kernel was originally based on the amazing work
done on
https://github.com/goatchurchprime/jupyter_micropython_remote.git

| Their original custom device connection library has been replaced by
  pyboard and mprepl to take advantage of proven functionality
  implemented there. mprepl has since been extended substantially.
| The kernel has also been reworked to extend form the full ipython
  kernel, so local cells are fully-functional and we can use the ipython
  display mechanisms for output formatting.
