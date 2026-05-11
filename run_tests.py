"""
Test Runner for Medical AI Chatbot
====================================
Comprehensive test execution script with multiple test categories.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py smoke              # Run smoke tests only
    python run_tests.py regression         # Run regression tests only
    python run_tests.py integration        # Run integration tests only
    python run_tests.py unit               # Run unit tests only
    python run_tests.py -v                 # Verbose output
    python run_tests.py --coverage         # Generate coverage report
    python run_tests.py --html             # Generate HTML report

Examples:
    python run_tests.py smoke -v
    python run_tests.py regression --coverage
    python run_tests.py integration -v --html
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent


def run_command(cmd, description):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print('='*60)
    
    result = subprocess.run(
        cmd,
        cwd=get_project_root(),
        shell=True,
        capture_output=False
    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description='Run Medical AI Chatbot Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py smoke -v           # Smoke tests with verbose
  python run_tests.py regression         # Regression tests
  python run_tests.py --coverage         # With coverage
        """
    )
    
    # Positional arguments
    parser.add_argument(
        'test_type',
        nargs='?',
        choices=['smoke', 'regression', 'integration', 'unit', 'all'],
        default='all',
        help='Type of tests to run (default: all)'
    )
    
    # Optional flags
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '-c', '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    
    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML report (requires pytest-html)'
    )
    
    parser.add_argument(
        '--tb', '--traceback',
        dest='traceback',
        choices=['short', 'long', 'line', 'native', 'no'],
        default='short',
        help='Traceback format (default: short)'
    )
    
    parser.add_argument(
        '-k',
        dest='keyword',
        help='Run tests matching the given keyword expression'
    )
    
    parser.add_argument(
        '--lf', '--last-failed',
        action='store_true',
        help='Run only tests that failed in the last run'
    )
    
    args = parser.parse_args()
    
    # Build pytest command
    cmd_parts = ['pytest', 'tests/']
    
    # Test type selection
    if args.test_type == 'smoke':
        cmd_parts.append('tests/test_smoke.py')
    elif args.test_type == 'regression':
        cmd_parts.append('tests/test_regression.py')
    elif args.test_type == 'integration':
        cmd_parts.append('tests/test_integration.py')
    elif args.test_type == 'unit':
        cmd_parts.append('tests/test_app.py')
    # 'all' runs all tests in tests/ directory
    
    # Add options
    if args.verbose:
        cmd_parts.append('-v')
    
    cmd_parts.extend(['--tb', args.traceback])
    
    if args.coverage:
        cmd_parts.extend(['--cov=app', '--cov=src', '--cov-report=term-missing'])
    
    if args.html:
        cmd_parts.append('--html=test_report.html --self-contained-html')
    
    if args.keyword:
        cmd_parts.extend(['-k', args.keyword])
    
    if args.last_failed:
        cmd_parts.append('--lf')
    
    # Add color and summary
    cmd_parts.append('--color=yes')
    cmd_parts.append('-ra')
    
    # Build command string
    cmd = ' '.join(cmd_parts)
    
    print(f"\nRunning: {args.test_type.upper()} tests")
    print(f"Command: {cmd}\n")
    
    # Run tests
    returncode = run_command(cmd, f"Running {args.test_type.upper()} Tests")
    
    # Summary
    print(f"\n{'='*60}")
    if returncode == 0:
        print("  ✓ ALL TESTS PASSED")
    else:
        print("  ✗ SOME TESTS FAILED")
    print('='*60)
    
    return returncode


if __name__ == '__main__':
    sys.exit(main())