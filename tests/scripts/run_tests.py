#!/usr/bin/env python3
"""
Test runner script for Photo Validation Service
Allows running tests with different levels of verbosity
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run command with result output."""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*50}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    
    return result.returncode == 0


def run_basic_tests():
    """Run basic unit tests only."""
    return run_command(
        "python -m pytest tests/unit/ -v",
        "Basic unit tests"
    )


def run_api_tests():
    """Run API and integration tests."""
    commands = [
        ("python -m pytest tests/unit/ -v", "Unit tests"),
        ("python -m pytest tests/integration/ -v", "Integration tests"),
    ]
    
    all_passed = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            all_passed = False
    
    return all_passed


def run_full_tests():
    """Run all available tests."""
    commands = [
        ("python -m pytest tests/unit/ -v --cov=app --cov-report=html", "Unit tests with coverage"),
        ("python -m pytest tests/integration/ -v", "Integration tests"),
        ("python -m pytest tests/ -k 'not slow' -v", "All fast tests"),
    ]
    
    all_passed = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            all_passed = False
    
    return all_passed


def main():
    """Main function for test runner."""
    parser = argparse.ArgumentParser(description="Test runner for Photo Validation Service")
    parser.add_argument(
        "mode", 
        choices=["basic", "api", "full"], 
        help="Test mode to run"
    )
    
    args = parser.parse_args()
    
    print(f"Starting tests in {args.mode} mode...")
    
    if args.mode == "basic":
        # Unit tests only, fast
        success = run_basic_tests()
    elif args.mode == "api":
        # API + CV tests without integration
        success = run_api_tests()
    elif args.mode == "full":
        # Complete test suite
        success = run_full_tests()
    else:
        print(f"Unknown mode: {args.mode}")
        sys.exit(1)
    
    if success:
        print(f"\n✅ All tests passed in {args.mode} mode!")
        sys.exit(0)
    else:
        print(f"\n❌ Some tests failed in {args.mode} mode!")
        sys.exit(1)


if __name__ == "__main__":
    main() 