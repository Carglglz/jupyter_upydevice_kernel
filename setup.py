from setuptools import setup

setup(name='jupyter_micropython_upydevice',
      version='0.0.1',
      description='Jupyter notebook kernel for operating Micropython.',
      author='Carlos Gil Gonzalez',
      author_email='carlosgilglez@gmail.com',
      keywords='jupyter micropython',
      url='https://github.com/goatchurchprime/jupyter_micropython_kernel',
      license='GPL3',
      packages=['mpy_kernel_upydevice'],
      install_requires=['pyserial', 'websocket', 'upydevice>=0.2.0'],
      extras_require={
        'mpy':  ["mpy-cross"],
      },
      setup_requires=['setuptools_scm']

)
