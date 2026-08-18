def test_v7_retry_state_and_diff_helper():
    from app.workflow.graph import get_clean_diff
    from app.config import settings
    assert callable(get_clean_diff)
    assert hasattr(settings, "max_retries")
