"""
Automated tests for CodeGraph AI AST Analyzer
Verifies static analysis, entity discovery, call resolution, and security guardrails.
"""

from pathlib import Path
import pytest
from app.parser.ast_analyzer import ASTAnalyzer


DEMO_REPO_PATH = str(Path(__file__).resolve().parent.parent.parent / "demo_repo")


@pytest.fixture
def analyzer() -> ASTAnalyzer:
    return ASTAnalyzer()


def test_1_file_discovery_in_demo_repo(analyzer: ASTAnalyzer):
    """Verify that Python files are discovered and relative paths are normalized."""
    result = analyzer.analyze_repository(DEMO_REPO_PATH)
    file_paths = {f.path for f in result.files}

    expected_files = {
        "main.py",
        "services/order_service.py",
        "services/payment_service.py",
        "services/discount_service.py",
        "utils/logger.py",
        "utils/unused_helpers.py",
    }
    for expected in expected_files:
        assert expected in file_paths, f"Expected {expected} to be discovered"

    assert len(result.files) >= 6


def test_2_function_extraction_and_line_numbers(analyzer: ASTAnalyzer):
    """Verify standalone functions, argument lists, and valid line numbers are extracted."""
    result = analyzer.analyze_repository(DEMO_REPO_PATH)
    logger_funcs = [f for f in result.functions if f.file_path == "utils/logger.py"]
    func_names = {f.name: f for f in logger_funcs}

    assert "format_log_entry" in func_names
    assert "log_info" in func_names
    assert "log_error" in func_names

    format_entry = func_names["format_log_entry"]
    assert format_entry.args == ["level", "message"]
    assert format_entry.start_line == 1
    assert format_entry.end_line >= format_entry.start_line
    assert not format_entry.is_method
    assert format_entry.scope == "global"


def test_3_class_and_method_extraction(analyzer: ASTAnalyzer):
    """Verify classes, methods, and class scoping are correctly recognized."""
    result = analyzer.analyze_repository(DEMO_REPO_PATH)
    classes = {c.name: c for c in result.classes if c.file_path == "services/discount_service.py"}

    assert "BaseDiscountRule" in classes
    assert "PercentageDiscountRule" in classes

    methods = [
        f for f in result.functions
        if f.file_path == "services/discount_service.py" and f.is_method
    ]
    method_names = {m.name: m for m in methods}

    assert "get_max_discount" in method_names
    assert method_names["get_max_discount"].scope == "BaseDiscountRule"

    assert "calculate_percentage_discount" in method_names
    assert method_names["calculate_percentage_discount"].scope == "PercentageDiscountRule"


def test_4_function_call_extraction_and_resolution(analyzer: ASTAnalyzer):
    """Verify cross-file and same-file function call resolution."""
    result = analyzer.analyze_repository(DEMO_REPO_PATH)

    # 1. In payment_service.py, process_order_payment calls charge_credit_card
    payment_calls = [
        c for c in result.calls
        if c.caller_file == "services/payment_service.py" and c.callee_name == "charge_credit_card"
    ]
    assert len(payment_calls) >= 1
    call = payment_calls[0]
    assert call.is_resolved is True
    assert "charge_credit_card" in (call.resolved_callee_id or "")

    # 2. In payment_service.py, charge_credit_card calls imported log_info
    log_calls = [
        c for c in result.calls
        if c.caller_file == "services/payment_service.py" and c.callee_name == "log_info"
    ]
    assert len(log_calls) >= 1
    assert log_calls[0].is_resolved is True
    assert "utils/logger.py" in (log_calls[0].resolved_callee_id or "")


def test_5_import_extraction_and_target_linking(analyzer: ASTAnalyzer):
    """Verify imports are correctly parsed and linked to relative file paths."""
    result = analyzer.analyze_repository(DEMO_REPO_PATH)
    order_imports = [imp for imp in result.imports if imp.source_file == "services/order_service.py"]

    imported_targets = {imp.imported_name: imp.resolved_file for imp in order_imports if imp.imported_name}

    assert "log_info" in imported_targets
    assert imported_targets["log_info"] == "utils/logger.py"

    assert "calculate_discount" in imported_targets
    assert imported_targets["calculate_discount"] == "services/discount_service.py"

    assert "process_order_payment" in imported_targets
    assert imported_targets["process_order_payment"] == "services/payment_service.py"


def test_6_class_inheritance_extraction(analyzer: ASTAnalyzer):
    """Verify subclass-to-superclass relationship detection."""
    result = analyzer.analyze_repository(DEMO_REPO_PATH)
    inheritances = [
        inh for inh in result.inheritances
        if inh.subclass_name == "PercentageDiscountRule"
    ]
    assert len(inheritances) == 1
    inh = inheritances[0]
    assert inh.superclass_name == "BaseDiscountRule"
    assert inh.resolved_superclass_id is not None
    assert "BaseDiscountRule" in inh.resolved_superclass_id


def test_7_unused_dead_code_detection(analyzer: ASTAnalyzer):
    """Verify that unused functions in demo_repo are accurately detected without false positives."""
    result = analyzer.analyze_repository(DEMO_REPO_PATH)
    unused = result.get_unused_functions()
    unused_names = {u.name for u in unused if u.file_path == "utils/unused_helpers.py"}

    # Both intentional dead helpers should be present
    assert "legacy_format_currency" in unused_names
    assert "calculate_vat_deprecated" in unused_names

    # Frequently used functions should NOT be marked unused
    called_names = {u.name for u in unused}
    assert "log_info" not in called_names
    assert "charge_credit_card" not in called_names
    assert "calculate_discount" not in called_names


def test_8_graceful_handling_of_syntax_errors(analyzer: ASTAnalyzer, tmp_path: Path):
    """Verify parser does not crash on malformed Python files and logs structured error."""
    broken_file = tmp_path / "broken_syntax.py"
    broken_file.write_text("def invalid_syntax_func(:", encoding="utf-8")

    result = analyzer.analyze_repository(str(tmp_path))

    assert len(result.errors) == 1
    err = result.errors[0]
    assert err["type"] == "SyntaxError"
    assert err["file"] == "broken_syntax.py"
    assert err["line"] == 1


def test_9_security_path_traversal_prevention(analyzer: ASTAnalyzer):
    """Verify invalid or nonexistent paths raise ValueError."""
    with pytest.raises(ValueError, match="does not exist or is not a directory"):
        analyzer.analyze_repository("c:/non_existent_folder_xyz_123")


def test_10_identical_function_names_in_different_files(analyzer: ASTAnalyzer, tmp_path: Path):
    """Verify functions with identical names in different files get unique, non-colliding IDs."""
    mod_a = tmp_path / "service_a.py"
    mod_a.write_text("def validate(data):\n    return True\n", encoding="utf-8")

    mod_b = tmp_path / "service_b.py"
    mod_b.write_text("def validate(data):\n    return False\n", encoding="utf-8")

    result = analyzer.analyze_repository(str(tmp_path))
    val_funcs = [f for f in result.functions if f.name == "validate"]

    assert len(val_funcs) == 2
    ids = {f.id for f in val_funcs}
    assert len(ids) == 2, "Function IDs must be unique across different files"
    assert "service_a.py" in val_funcs[0].id or "service_a.py" in val_funcs[1].id
    assert "service_b.py" in val_funcs[0].id or "service_b.py" in val_funcs[1].id
