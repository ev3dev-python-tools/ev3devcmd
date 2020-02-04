
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2020-01-31

### ADDED
- First production release which can be use with the thonny-ev3dev plugin in the Thonny IDE version 3. 
- the mirror and cleanup commands also allow you to use a subdir of the homedir on the EV3 robot instead
  of the homedir.

### CHANGED
- created new project  https://github.com/ev3dev-python-tools/ev3devcmd
  by splitting of ev3devcmd python library from the thonny-ev3dev project at its
  old website https://github.com/harcokuppens/thonny-ev3dev/
- for CHANGELOG before 1.0.0 look at the old website at https://github.com/harcokuppens/thonny-ev3dev/
- temporary we applied the hack to put a copy of the sftpclone package within this package to
  resolve a version conflict when requiring the paramiko package. When new a new version of the sftpclone 
  package arrives we will remove this hack. 
- reorganized code so that all code and resources are within the ev3devcmd package folder  
- added entry script in setup.py instead of old script: ev3dev command now available on linux/windows/macos
