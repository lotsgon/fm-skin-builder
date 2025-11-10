"""
PyInstaller hook for bundling Cairo library with the application.
This ensures cairosvg/cairocffi can find the native Cairo library.
"""
import os
import sys
from pathlib import Path

# Collect data files
datas = []

# Collect binaries - we need to find and bundle the Cairo library
binaries = []

# Try to find Cairo library location
def find_cairo_library():
    """Attempt to locate Cairo library on the system."""
    import cairocffi

    # cairocffi tries to load these library names
    lib_names = {
        'win32': ['cairo-2.dll', 'cairo.dll', 'libcairo-2.dll'],
        'darwin': ['libcairo.2.dylib', 'libcairo.dylib'],
        'linux': ['libcairo.so.2', 'libcairo.so']
    }

    platform = sys.platform
    if platform == 'win32':
        search_names = lib_names['win32']
    elif platform == 'darwin':
        search_names = lib_names['darwin']
    else:
        search_names = lib_names['linux']

    # Try to find Cairo in common locations
    search_paths = []

    if platform == 'win32':
        # Windows: Check MSYS2, GTK installation paths, conda, pip packages
        potential_paths = [
            Path('C:/msys64/mingw64/bin'),       # MSYS2 (default location)
            Path(sys.prefix) / 'DLLs',           # Python DLLs directory
            Path(sys.prefix) / 'Library' / 'bin', # Conda
            Path(sys.prefix) / 'bin',
            Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'GTK3-Runtime' / 'bin',
        ]
        search_paths.extend([p for p in potential_paths if p.exists()])
    elif platform == 'darwin':
        # macOS: Check Homebrew paths
        potential_paths = [
            Path('/opt/homebrew/lib'),  # ARM Homebrew
            Path('/usr/local/lib'),      # Intel Homebrew
            Path(sys.prefix) / 'lib',
        ]
        search_paths.extend([p for p in potential_paths if p.exists()])
    else:
        # Linux: Check system paths
        potential_paths = [
            Path('/usr/lib/x86_64-linux-gnu'),
            Path('/usr/lib'),
            Path('/usr/local/lib'),
            Path(sys.prefix) / 'lib',
        ]
        search_paths.extend([p for p in potential_paths if p.exists()])

    # Search for Cairo library
    for search_path in search_paths:
        for lib_name in search_names:
            lib_path = search_path / lib_name
            if lib_path.exists():
                return str(lib_path)

    return None

try:
    cairo_lib = find_cairo_library()
    if cairo_lib:
        # Bundle the Cairo library
        binaries.append((cairo_lib, '.'))
        print(f"[hook-cairocffi] Found and bundling Cairo library: {cairo_lib}")
    else:
        print("[hook-cairocffi] WARNING: Could not locate Cairo library on system")
        print("[hook-cairocffi] Application may fail at runtime if Cairo is not installed")
except Exception as e:
    print(f"[hook-cairocffi] Error while searching for Cairo: {e}")
