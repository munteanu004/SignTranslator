"""Test aitviewer interactive mode"""
import sys
import os
import traceback

try:
    print("Testing aitviewer interactive viewer...")

    # Test PyQt5
    print("1. Testing PyQt5...")
    from PyQt5 import QtWidgets
    print("   PyQt5 OK")

    # Test aitviewer imports
    print("2. Testing aitviewer imports...")
    from aitviewer.viewer import Viewer
    from aitviewer.renderables.smpl import SMPLSequence
    from aitviewer.configuration import CONFIG as C
    print("   aitviewer imports OK")

    # Try to create viewer
    print("3. Creating viewer...")
    viewer = Viewer(size=(800, 600))
    print("   Viewer created!")

    print("\nSUCCESS! Viewer should be running now.")
    print("Close the viewer window to exit.")

    viewer.run()

except Exception as e:
    print(f"\nERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
