"""Local override of the PyOpenGL hook for the MikroCAM Windows binary.

The contributed hook collects every file in OpenGL/DLLS (32/64-bit freeglut and GLE builds
for vc9/vc10/vc14). They pull MSVCR90/MSVCR100 from the build machine, and MikroCAM never
uses GLUT or GLE: VisPy drives the system OpenGL context created by Qt.
"""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['OpenGL.platform.win32'] + collect_submodules('OpenGL.arrays')
