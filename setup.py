from setuptools import setup


def readme():
    with open('README.rst', 'r', encoding="utf-8") as f:
        return f.read()


setup(name='jupyter_micropython_upydevice',
      version='0.0.3',
      description='Jupyter kernel based on upydevice for operating MicroPython',
      long_description=readme(),
      long_description_content_type='text/x-rst',
      author='Carlos Gil Gonzalez',
      author_email='carlosgilglez@gmail.com',
      keywords='jupyter micropython upydevice',
      url='https://github.com/Carglglz/jupyter_upydevice_kernel',
      license='GPL3',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: System :: Monitoring',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Terminals'
      ],
      packages=['mpy_kernel_upydevice'],
      install_requires=['upydevice>=0.2.2'],
      setup_requires=['setuptools_scm'])
