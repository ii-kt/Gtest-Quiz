import pytest

pytestmark = pytest.mark.e2e
pytest.skip('Legacy Streamlit smoke disabled after backend/frontend split.', allow_module_level=True)
