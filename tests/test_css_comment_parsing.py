"""Tests for CSS comment parsing to prevent commented-out overrides from being applied."""

from pathlib import Path
import tempfile
from fm_skin_builder.core.css_utils import load_css_properties, load_css_vars


def test_load_css_properties_ignores_comments():
    """Test that commented-out CSS variables are not parsed."""
    css_content = """
    /* Commented out - should NOT be parsed */
    /* --border-radius-radius-8: 0px;
       --border-radius-radius-12: 0px; */

    /* This is active */
    --border-radius-radius-16: 16px;

    /* Another comment
       --test-var: 999px;
    */

    --active-var: 20px;
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".uss", delete=False) as f:
        f.write(css_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        props = load_css_properties(temp_path)

        # Should NOT contain commented-out variables
        assert "--border-radius-radius-8" not in props
        assert "--border-radius-radius-12" not in props
        assert "--test-var" not in props

        # Should contain active variables
        assert "--border-radius-radius-16" in props
        assert props["--border-radius-radius-16"] == "16px"
        assert "--active-var" in props
        assert props["--active-var"] == "20px"

        # Total should be 2 (only active variables)
        assert len(props) == 2
    finally:
        temp_path.unlink()


def test_load_css_vars_ignores_comments():
    """Test that load_css_vars also ignores commented-out variables."""
    css_content = """
    /* --test-color: #FF0000; */
    --active-color: #00FF00;
    /* Multi-line
       comment with
       --hidden-color: #0000FF;
    */
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".uss", delete=False) as f:
        f.write(css_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        vars = load_css_vars(temp_path)

        # Should NOT contain commented-out colors
        assert "--test-color" not in vars
        assert "--hidden-color" not in vars

        # Should contain active color
        assert "--active-color" in vars
        assert vars["--active-color"] == "#00FF00"

        assert len(vars) == 1
    finally:
        temp_path.unlink()


def test_inline_comments_handled_correctly():
    """Test that inline comments don't break parsing."""
    css_content = """
    --var-1: 10px; /* inline comment */
    /* --commented-var: 20px; */ --var-2: 30px;
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".uss", delete=False) as f:
        f.write(css_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        props = load_css_properties(temp_path)

        # Should contain var-1 and var-2
        assert "--var-1" in props
        assert "--var-2" in props
        assert "--commented-var" not in props

        assert props["--var-1"] == "10px"
        assert props["--var-2"] == "30px"
    finally:
        temp_path.unlink()
