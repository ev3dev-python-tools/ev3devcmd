from setuptools import setup
import os.path
import sys


setup(
      name="ev3devcmd",
      version="1.0.0",
      description="ev3devcmd library and cmdline utility",
      long_description="""
ev3devcmd library and cmdline utility

For more info: https://github.com/ev3dev-python-tools/ev3devcmd
""",
      url="https://github.com/ev3dev-python-tools/ev3devcmd",
      author="Harco Kuppens",
      author_email="h.kuppens@cs.ru.nl",
      license="MIT",
      classifiers=[
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "License :: Freeware",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Education",
        "Topic :: Software Development",
      ],
      keywords="IDE education programming EV3 mindstorms lego",
      platforms=["Windows", "macOS", "Linux"],
      python_requires=">=3.6",

      # TEMPORARY HACK:
      # We use a mirror of sftpclone v1.2.2, because it has explicit dependency 'paramiko==2.4.1',
      # but we need 'paramiko==2.6.0' for ev3devcmd!
      # When we used sftpclone v1.2.2 as dependency, then the entry script would thrown an version conflict error
      # because ev3devcmd needs 'paramiko==2.6.0' and sftpclone needs 'paramiko==2.4.1'.
      # But sftpclone v1.2.2 works fine with the newer 'paramiko==2.6.0', so we took the HACK to include a mirror of it,
      # into this ev3devcmd package until a newer version of it requiring 'paramiko==2.6.0' would be available.
      # This HACK solves the dependency problem, because we then don't need the requirement for 'sftpclone=1.2.2' anymore.
      # so:  removed 'sftpclone==1.2.2' from install_requires, and added  'ev3devcmd.sftpclone' to packages
      install_requires=['ev3devlogging','paramiko==2.6.0','rpyc==4.1.2'],
      #instead of ['ev3devlogging','paramiko==2.6.0','sftpclone==1.2.2','rpyc==4.1.2'],
      packages=['ev3devcmd'],
      #instead of ['ev3devcmd'],

      package_data={'ev3devcmd': ['res/*']},

      entry_points={
                 'console_scripts': [
                     'ev3dev = ev3devcmd.__main__:main'
                 ]
    },
)
