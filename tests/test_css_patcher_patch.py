from pathlib import Path
from types import SimpleNamespace
from src.core.css_patcher import CssPatcher, hex_to_rgba
import builtins


class FakeColor:
    def __init__(self, r=0.0, g=0.0, b=0.0, a=1.0):
        self.r, self.g, self.b, self.a = r, g, b, a


class FakeValue:
    def __init__(self, t, idx):
        self.m_ValueType = t
        self.valueIndex = idx


class FakeProperty:
    def __init__(self, name, values):
        self.m_Name = name
        self.m_Values = values


class FakeRule:
    def __init__(self, props):
        self.m_Properties = props


class FakeSelPart:
    def __init__(self, val, typ):
        self.m_Value = val
        self.m_Type = typ


class FakeSelector:
    def __init__(self, parts):
        self.m_Parts = parts


class FakeComplexSelector:
    def __init__(self, rule_index, selectors):
        self.ruleIndex = rule_index
        self.m_Selectors = selectors


class FakeData:
    def __init__(self, name, strings, colors, rules, complex_selectors=None):
        self.m_Name = name
        self.strings = strings
        self.colors = colors
        self.m_Rules = rules
        self.m_ComplexSelectors = complex_selectors or []

    def save(self):
        self._saved = True


class FakeObjType:
    def __init__(self, name):
        self.name = name


class FakeObj:
    def __init__(self, data):
        self.type = FakeObjType("MonoBehaviour")
        self._data = data

    def read(self):
        return self._data


class FakeFile:
    def save(self):
        return b"bundle-bytes"


class FakeEnv:
    def __init__(self, objects):
        self.objects = objects
        self.file = FakeFile()


def set_unitypy_in_module(cp_mod, env):
    cp_mod.UnityPy = SimpleNamespace(load=lambda path: env)


def test_var_based_patch_and_save(tmp_path: Path):
    # Setup a stylesheet that references strings[0] both as var (type 3) and color (type 4)
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--primary"]
    rule = FakeRule([
        FakeProperty("color", [FakeValue(3, 0), FakeValue(4, 0)])
    ])
    data = FakeData("Style", strings, colors, [rule])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)

    out_dir = tmp_path / "out"
    patcher = cp.CssPatcher(css_vars={
                            "--primary": "#FF0000"}, selector_overrides={}, patch_direct=False, debug_export_dir=None)
    patcher.patch_bundle_file(tmp_path / "fm_base.bundle", out_dir)

    # Verify color was patched to red
    r, g, b, a = colors[0].r, colors[0].g, colors[0].b, colors[0].a
    assert (r, g, b, a) == (1.0, 0.0, 0.0, 1.0)
    # Verify output bundle exists with original name
    assert (out_dir / "fm_base.bundle").exists()


def test_selector_override_patch(tmp_path: Path):
    # Build a rule with color value type=4 at color index 0, and a selector .green
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = []
    rule = FakeRule([
        FakeProperty("color", [FakeValue(4, 0)])
    ])
    sel = FakeComplexSelector(0, [FakeSelector([FakeSelPart("green", 3)])])
    data = FakeData("Style2", strings, colors, [rule], [sel])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)

    out_dir = tmp_path / "out2"
    patcher = cp.CssPatcher(css_vars={}, selector_overrides={(
        ".green", "color"): "#00FF00"}, patch_direct=False, debug_export_dir=None)
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    # Verify color patched to green
    r, g, b, a = colors[0].r, colors[0].g, colors[0].b, colors[0].a
    assert (r, g, b) == (0.0, 1.0, 0.0)


def test_selector_override_converts_string_handles(tmp_path: Path):
    # If a selector override targets a property with only string handles, convert one to a literal color
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--colours-linear-scale-20",
               "--colours-data-ratings-star-ability-orange"]
    prop = FakeProperty("color", [FakeValue(10, 0), FakeValue(8, 1)])
    rule = FakeRule([prop])
    selector = FakeComplexSelector(0, [FakeSelector(
        [FakeSelPart("attribute-colour-great", 3)])])
    data = FakeData("StyleStrings", strings, colors, [rule], [selector])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)

    out_dir = tmp_path / "out_selector_strings"
    target_hex = "#81848D"
    patcher = cp.CssPatcher(
        css_vars={},
        selector_overrides={(".attribute-colour-great", "color"): target_hex},
        patch_direct=False,
        debug_export_dir=None,
    )
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    # A new color entry should have been appended and the first handle converted to color
    assert len(colors) == 2
    converted = prop.m_Values[0]
    assert converted.m_ValueType == 4
    assert converted.valueIndex == 1
    new_color = colors[1]
    R, G, B, A = hex_to_rgba(target_hex)
    assert (new_color.r, new_color.g, new_color.b, new_color.a) == (R, G, B, A)


def test_patch_direct_literal(tmp_path: Path):
    # color property with type 4, no var link; patch_direct should match '--foo-color' endswith 'color'
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = []
    rule = FakeRule([
        FakeProperty("color", [FakeValue(4, 0)])
    ])
    data = FakeData("Style3", strings, colors, [rule])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)
    out_dir = tmp_path / "out3"
    patcher = cp.CssPatcher(css_vars={"--foo-color": "#112233"},
                            selector_overrides={}, patch_direct=True, debug_export_dir=None)
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    # Verify color patched to #112233
    r, g, b, a = colors[0].r, colors[0].g, colors[0].b, colors[0].a
    R, G, B, A = hex_to_rgba("#112233")
    assert (r, g, b, a) == (R, G, B, A)


def test_debug_export_writes_files(tmp_path: Path):
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--primary"]
    rule = FakeRule([
        FakeProperty("color", [FakeValue(3, 0), FakeValue(4, 0)])
    ])
    data = FakeData("DebugStyle", strings, colors, [rule])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)
    out_dir = tmp_path / "out4"
    debug_dir = out_dir / "debug_uss"
    patcher = cp.CssPatcher(css_vars={"--primary": "#0000FF"}, selector_overrides={
    }, patch_direct=False, debug_export_dir=debug_dir)
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    files = {p.name for p in debug_dir.iterdir()}
    assert any(n.startswith("original_") and n.endswith(".uss") for n in files)
    assert any(n.startswith("patched_") and n.endswith(".uss") for n in files)


def test_root_level_variable_applies_when_strings_names_var(tmp_path: Path):
    # No rule references the var directly; strings[0] names the var and colors[0]
    # should be updated from the css_vars mapping.
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--root-accent"]
    data = FakeData("RootStyle", strings, colors, [])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)

    out_dir = tmp_path / "out_root"
    patcher = cp.CssPatcher(css_vars={"--root-accent": "#00FFFF"},
                            selector_overrides={}, patch_direct=False, debug_export_dir=None)
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    # Verify color was patched to #00FFFF
    R, G, B, A = hex_to_rgba("#00FFFF")
    r, g, b, a = colors[0].r, colors[0].g, colors[0].b, colors[0].a
    assert (r, g, b, a) == (R, G, B, A)


def test_root_level_literal_variable_updates(tmp_path: Path):
    colors = [FakeColor(0.2, 0.2, 0.2, 1.0)]
    strings: list[str] = []
    prop = FakeProperty("--literal-accent", [FakeValue(4, 0)])
    data = FakeData("LiteralRoot", strings, colors, [FakeRule([prop])])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)

    out_dir = tmp_path / "out_literal"
    target = "#CC0714"
    patcher = cp.CssPatcher(css_vars={"--literal-accent": target},
                            selector_overrides={}, patch_direct=False, debug_export_dir=None)
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    R, G, B, A = hex_to_rgba(target)
    col = colors[0]
    assert (col.r, col.g, col.b, col.a) == (R, G, B, A)


def test_variable_reference_converted_to_literal_color(tmp_path: Path):
    # Root variable defined via var(--other); expect conversion into literal color with new entry
    colors = [FakeColor(0.1, 0.1, 0.1, 1.0)]
    strings = ["--other-token"]
    prop = FakeProperty("--global-text-primary",
                        [FakeValue(10, 0), FakeValue(2, 0)])
    rule = FakeRule([prop])
    data = FakeData("RefStyle", strings, colors, [rule])
    env = FakeEnv([FakeObj(data)])

    from src.core import css_patcher as cp
    set_unitypy_in_module(cp, env)

    out_dir = tmp_path / "out_var_literal"
    hex_colour = "#050B14"
    patcher = cp.CssPatcher(css_vars={"--global-text-primary": hex_colour},
                            selector_overrides={}, patch_direct=False, debug_export_dir=None)
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    # A new color entry should have been appended and the property converted to a literal color handle
    assert len(colors) == 2
    assert len(prop.m_Values) == 2
    handle = prop.m_Values[0]
    assert handle.m_ValueType == 4
    assert handle.valueIndex == 1

    new_color = colors[1]
    R, G, B, A = hex_to_rgba(hex_colour)
    assert (new_color.r, new_color.g, new_color.b, new_color.a) == (R, G, B, A)
