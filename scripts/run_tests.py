#!/usr/bin/env python3
"""
Test runner script for ICB Backend v3.

Provides comprehensive test execution with different categories and options.
"""

import argparse
import subprocess
import sys
import time
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    elapsed_time = time.time() - start_time
    
    print(f"Exit code: {result.returncode}")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    
    return result.returncode == 0, elapsed_time


def run_unit_tests():
    """Run unit tests."""
    command = "python -m pytest tests/unit/ tests/parser/ tests/validator/ -v --cov=src --cov-report=term-missing"
    return run_command(command, "Unit Tests")


def run_integration_tests():
    """Run integration tests."""
    command = "python -m pytest tests/integration/ -v --cov=src --cov-report=term-missing"
    return run_command(command, "Integration Tests")


def run_contract_tests():
    """Run contract tests."""
    command = "python -m pytest tests/contract/ -v --cov=src --cov-report=term-missing"
    return run_command(command, "Contract Tests")


def run_performance_tests():
    """Run performance tests."""
    command = "python -m pytest tests/performance/ -v --benchmark-only"
    return run_command(command, "Performance Tests")


def run_sample_data_tests():
    """Run sample data tests."""
    command = "python -m pytest tests/integration/test_sample_data_orchestration.py -v"
    return run_command(command, "Sample Data Tests")


def run_database_tests():
    """Run database tests."""
    command = "python -m pytest tests/database/ -v"
    return run_command(command, "Database Tests")


def run_all_tests():
    """Run all tests."""
    command = "python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=xml"
    return run_command(command, "All Tests")


def run_linting():
    """Run linting checks."""
    commands = [
        ("python -m flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__", "Flake8 Linting"),
        ("python -m black --check src/ tests/", "Black Formatting Check"),
        ("python -m isort --check-only src/ tests/", "Import Sorting Check"),
        ("python -m mypy src/ --ignore-missing-imports", "Type Checking")
    ]
    
    results = []
    for command, description in commands:
        success, elapsed_time = run_command(command, description)
        results.append((success, elapsed_time))
    
    return all(success for success, _ in results), sum(elapsed_time for _, elapsed_time in results)


def run_security_scan():
    """Run security scanning."""
    commands = [
        ("python -m bandit -r src/ -f json -o bandit-report.json", "Bandit Security Scan"),
        ("python -m safety check --json --output safety-report.json", "Safety Dependency Scan")
    ]
    
    results = []
    for command, description in commands:
        success, elapsed_time = run_command(command, description)
        results.append((success, elapsed_time))
    
    return all(success for success, _ in results), sum(elapsed_time for _, elapsed_time in results)


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="ICB Backend v3 Test Runner")
    parser.add_argument("--category", choices=[
        "unit", "integration", "contract", "performance", 
        "sample-data", "database", "all", "lint", "security"
    ], default="all", help="Test category to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--xml", action="store_true", help="Generate XML coverage report")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--max-fail", type=int, default=5, help="Maximum number of failures")
    
    args = parser.parse_args()
    
    print("ICB Backend v3 Test Runner")
    print("=" * 50)
    
    # Set environment variables
    os.environ["PYTHONPATH"] = str(Path.cwd())
    
    # Track overall results
    total_start_time = time.time()
    results = []
    
    try:
        if args.category == "unit":
            success, elapsed_time = run_unit_tests()
            results.append(("Unit Tests", success, elapsed_time))
            
        elif args.category == "integration":
            success, elapsed_time = run_integration_tests()
            results.append(("Integration Tests", success, elapsed_time))
            
        elif args.category == "contract":
            success, elapsed_time = run_contract_tests()
            results.append(("Contract Tests", success, elapsed_time))
            
        elif args.category == "performance":
            success, elapsed_time = run_performance_tests()
            results.append(("Performance Tests", success, elapsed_time))
            
        elif args.category == "sample-data":
            success, elapsed_time = run_sample_data_tests()
            results.append(("Sample Data Tests", success, elapsed_time))
            
        elif args.category == "database":
            success, elapsed_time = run_database_tests()
            results.append(("Database Tests", success, elapsed_time))
            
        elif args.category == "lint":
            success, elapsed_time = run_linting()
            results.append(("Linting", success, elapsed_time))
            
        elif args.category == "security":
            success, elapsed_time = run_security_scan()
            results.append(("Security Scan", success, elapsed_time))
            
        elif args.category == "all":
            # Run all test categories
            categories = [
                ("Linting", run_linting),
                ("Unit Tests", run_unit_tests),
                ("Integration Tests", run_integration_tests),
                ("Contract Tests", run_contract_tests),
                ("Performance Tests", run_performance_tests),
                ("Sample Data Tests", run_sample_data_tests),
                ("Database Tests", run_database_tests),
                ("Security Scan", run_security_scan)
            ]
            
            for name, func in categories:
                success, elapsed_time = func()
                results.append((name, success, elapsed_time))
                
                if not success and args.fail_fast:
                    print(f"\n❌ {name} failed, stopping due to --fail-fast")
                    break
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    
    # Print summary
    total_elapsed_time = time.time() - total_start_time
    print(f"\n{'='*60}")
    print("TEST EXECUTION SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for name, success, elapsed_time in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name:<20} {status:<10} {elapsed_time:>8.2f}s")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"{'='*60}")
    print(f"Total execution time: {total_elapsed_time:.2f}s")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print(f"\n❌ {failed} test category(ies) failed")
        sys.exit(1)
    else:
        print(f"\n✅ All {passed} test category(ies) passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
