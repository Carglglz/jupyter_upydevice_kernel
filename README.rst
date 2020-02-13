Jupyter MicroPython Upydevice Kernel
=====================================

Jupyter kernel to interact with a MicroPython board over its REPL
interface.

Typically used with MicroPython boards over the USB / Serial interface,
or through the WebREPL.

MicroPython
-----------
Tested on MicroPython v1.11 and v1.12

Background
----------

This Jupyter MicroPython Kernel is heavily based on the amazing work
done on https://github.com/goatchurchprime/jupyter_micropython_remote.git
and https://github.com/andrewleech/jupyter_micropython_remote

Their device connection library has been replaced by
upydevice latest classes ``SERIAL_DEVICE`` and ``WS_DEVICE`` that allows both serial and
websocket (WebREPL) connections.
The kernel has also been reworked to support autocompletions on tab which works
for MicroPython, iPython and %cell magic commands.


Installation
------------

Ensure you have a new enough MicroPython installed on your board (see above).

You also need python 3.6 or above, ensuring it’s available from your current
command line. Optionally (recommended) use your favourite pipenv / virtualenv to set
up a clean environment to run jupyter from.

Then install this module:

::

   pip install jupyter_micropython_upydevice

Install the kernel into jupyter itself using the shell command:

::

   python -m mpy_kernel_upydevice.install

This registers the kernel with Jupyter so it can be selected for use in
notebooks

Running
-------

Now run Jupyter notebooks or Jupyter lab:

For Jupyter lab do:

::

   jupyter lab

In the launcher click on the MicroPython upydevice button to create a new notebook


To connect through serial/USB: ``%serialconnect [SERIAL PORT] [BAUDRATE]``

This command has autocompletion on tab, so hit tab and select a port from the list

Baudrate default is 115200

eg:
::

   %serialconnect /dev/tty.usbmodem3370377430372 115200



::

    ** Serial connected **

    /dev/tty.usbmodem3370377430372

    MicroPython v1.12-156-g0852acfc7 on 2020-02-11; PYBv1.1 with STM32F405RG
    Type "help()" for more information.

To connect through WebREPL: ``%websocketconnect [IP] --password "[PASSWORD]"``

eg:

::

    %websocketconnect 192.168.1.42 --password "mypass"


::

    ** WebREPL connected **

    MicroPython v1.12-63-g1c849d63a on 2020-01-14; ESP32 module with ESP32
    Type "help()" for more information.

You should now be able to execute MicroPython commands by running the
cells.

There is a *upydevie_kernel_demo.ipynb* file in the directory you could look at
with some of the features shown.

If a cell is taking too long, or if you want to stop an ongoing loop
To interrupt / ^C use “Interrupt the kernel” button and this will raise a ``KeyboardInterrupt``
in the device.

Alternatively hit Escape and then ‘i’ twice.

To do a soft reset (it will reconnect automatically) type:

::

   %rebootdevice




  Note: Restarting the kernel does not actually reboot the device.
  Also, pressing the reset button will mess things up (at least for WebREPL,
  and for serial this is probably true as well).

%Cell magic Commands
--------------------
Cell magic commands have autocompletion on tab, so hit tab and see what Commands
are available, or to see more information about each command do:
::

   %lsmagic


::

    %disconnect
      disconnects device

    %lsmagic
      list magic commands

    %rebootdevice
      reboots device

    %is_reachable
      Test if device is reachable (must be connected first)

    %serialconnect [portname] [baudrate]
      connects to a device over USB, default baudrate is 115200

    %websocketconnect [websocketurl] [--password PASSWORD]
      connects to the WebREPL over wifi (WebREPL daemon must be running)
      websocketurl defaults to 192.168.4.1 (uri -> ws://192.168.4.1:8266)

    %meminfo
      Shows RAM size/used/free/use% info

    %whoami
      Shows Device name, port, id, and system info

    %gccollect
      To use the garbage collector and free some RAM if possible

    %local
      To run the cell contents in local iPython

    %sync
      To sync a variable/output data structure of the device into iPython
      if no var name provided it stores the output into _

The communications interface to the micropython module is based on `upydevice
<https://github.com/Carglglz/upydevice>`_ new classes ``SERIAL_DEVICE`` and ``WS_DEVICE``


This is also the core library of `upydev
<https://github.com/Carglglz/upydev>`_ The SERIAL SHELL-REPL can be used simultaneously
with the upydevice Kernel since the serial connection is non-blocking.

%local
------
Individual cells can also be run on the local iPython instead of the MicroPython
kernel by starting a cell with ``%local``

This can be useful to work directly with local files, use ipywidgets, etc.
Commands here will be run by the standard ipython kernel.

In `%local` cells, a special global function ``remote()`` is also available which
will pass a single string argument to the MicroPython board to be run, returning
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

%sync
-----
Any variable/output of the device can be stored in local iPython easily.
If a var name is not provided the output will be stored locally in _ , e.g. :
::

    %sync
    [1,2,3,5]

::

  [1, 2, 3, 5]


::

    %local
    _

::

  [1, 2, 3, 5]


If device output is assigned to a variable it will be stored locally with the
same name e.g. :

::

    %sync
    my_data = {'key1':[1,2,3], 'key2':[4,5,6]}


::

    %local
    my_data


::

    {'key2': [4, 5, 6], 'key1': [1, 2, 3]}





This works for any type of output (bytes/bytearrays/arrays/ints/floats/strings/lists/dicts etc..)
