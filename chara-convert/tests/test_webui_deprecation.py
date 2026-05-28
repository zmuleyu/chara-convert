import warnings
import pytest


def test_webui_import_warns():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            import importlib
            import chara_convert.webui  # noqa: F401
            importlib.reload(chara_convert.webui)
        except ImportError:
            pass  # gradio not installed; deprecation should still have fired
    msgs = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert any("deprecated" in m for m in msgs)
