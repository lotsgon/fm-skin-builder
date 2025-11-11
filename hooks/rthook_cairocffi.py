"""
PyInstaller runtime hook for cairocffi.
This hook helps cairocffi find the Cairo DLL when running from a PyInstaller bundle.
"""
import os
import sys

# When running from PyInstaller, sys._MEIPASS contains the path to the extracted files
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    dll_directory = sys._MEIPASS

    if sys.platform == 'win32':
        # CRITICAL: Add _MEIPASS to the BEGINNING of PATH
        # This ensures Windows finds our bundled DLLs first
        os.environ['PATH'] = dll_directory + os.pathsep + os.environ.get('PATH', '')

        # Python 3.8+: Add to DLL search directories
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(dll_directory)
            except (OSError, AttributeError):
                pass

        # CRITICAL FIX: Pre-load Cairo DLL and its dependencies before cairocffi tries to find them
        # This forces Windows to load the DLLs and makes them available system-wide
        try:
            import ctypes

            # Pre-load dependencies in the correct order (dependencies first, then Cairo)
            # This ensures all required DLLs are available when Cairo loads
            dependency_order = [
                # Core runtime (must be first)
                'libwinpthread-1.dll',
                'libgcc_s_seh-1.dll',
                'libstdc++-6.dll',
                # Basic libraries
                'zlib1.dll',
                'libbz2-1.dll',
                'libiconv-2.dll',
                'libintl-8.dll',
                # Image/compression
                'libpng16-16.dll',
                'libbrotlicommon.dll',
                'libbrotlidec.dll',
                # GLib and deps
                'libffi-8.dll',
                'libpcre2-8-0.dll',
                'libglib-2.0-0.dll',
                # Font libraries
                'libexpat-1.dll',
                'libfreetype-6.dll',
                'libgraphite2.dll',
                'libharfbuzz-0.dll',
                'libfontconfig-1.dll',
                # Graphics
                'libpixman-1-0.dll',
                # Finally, Cairo itself
                'libcairo-2.dll',
            ]

            loaded_count = 0
            for dll_name in dependency_order:
                dll_path = os.path.join(dll_directory, dll_name)
                if os.path.exists(dll_path):
                    try:
                        ctypes.CDLL(dll_path)
                        loaded_count += 1
                    except OSError:
                        # Some DLLs might fail to load individually, that's okay
                        pass

        except Exception:
            # If pre-loading fails, cairocffi will try its own loading
            pass

    elif sys.platform == 'darwin':
        # macOS: Set library path
        os.environ['DYLD_LIBRARY_PATH'] = dll_directory + os.pathsep + os.environ.get('DYLD_LIBRARY_PATH', '')
    else:
        # Linux: Set library path
        os.environ['LD_LIBRARY_PATH'] = dll_directory + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')


