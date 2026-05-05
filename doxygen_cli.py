#!/usr/bin/env python3
"""
Terminal API for Doxygen Documentation Validator
Allows batch processing of files and folders
"""

import argparse
import os
import sys
from pathlib import Path
from doxygen_validator import DoxygenValidator


def process_file(file_path: str, validator: DoxygenValidator, args) -> bool:
    """
    Process a single file
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"Processing: {file_path}")
    print(f"{'='*80}")
    
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Validate
        print("Validating...")
        result = validator.validate_file(content)
        
        print(f"  Total entities: {result['total_entities']}")
        print(f"  Issues found: {result['issues_found']}")
        
        if result['issues_found'] == 0:
            print("  ✅ No issues found - file is compliant")
            return True
        
        # Show issues if requested
        if args.verbose:
            print("\n  Issues:")
            for issue in result['issues'][:10]:  # Show first 10
                entity = issue['entity']
                entity_name = entity.get('name', entity.get('class', 'Unknown'))
                print(f"    - Line {entity['line']}: {entity['type']} '{entity_name}' - {issue['issue_type']}")
            if result['issues_found'] > 10:
                print(f"    ... and {result['issues_found'] - 10} more")
        
        # Fix if requested
        if args.fix:
            print("\n  Fixing issues...")
            fixed_content = validator.fix_file(content, result)
            
            # Check if content changed (verification might have rejected it)
            if fixed_content == content:
                print("  ⚠️  No changes made (verification may have failed)")
                return False
            
            # Write back
            if args.in_place:
                # Backup original
                if args.backup:
                    backup_path = file_path + '.bak'
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  💾 Backup saved: {backup_path}")
                
                # Write fixed version
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"  ✅ Fixed and saved: {file_path}")
            else:
                # Write to output file
                output_path = args.output or (file_path.replace('.h', '_fixed.h'))
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"  ✅ Fixed version saved: {output_path}")
            
            return True
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error processing file: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


def find_header_files(path: str, recursive: bool = False) -> list:
    """Find all .h and .hpp files in a directory"""
    path_obj = Path(path)
    
    if path_obj.is_file():
        return [str(path_obj)]
    
    if recursive:
        return [str(p) for p in path_obj.rglob('*.h')] + [str(p) for p in path_obj.rglob('*.hpp')]
    else:
        return [str(p) for p in path_obj.glob('*.h')] + [str(p) for p in path_obj.glob('*.hpp')]


def main():
    parser = argparse.ArgumentParser(
        description='Doxygen Documentation Validator - Terminal API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single file
  python doxygen_cli.py file.h
  
  # Validate and fix a file (save to new file)
  python doxygen_cli.py file.h --fix
  
  # Fix in-place with backup
  python doxygen_cli.py file.h --fix --in-place --backup
  
  # Process all .h files in a directory
  python doxygen_cli.py src/ --fix --in-place
  
  # Process recursively
  python doxygen_cli.py src/ --fix --in-place --recursive
  
  # Disable code verification (allow code changes)
  python doxygen_cli.py file.h --fix --no-verify
        """
    )
    
    parser.add_argument('path', help='File or directory to process')
    parser.add_argument('--fix', action='store_true', help='Fix issues (default: validate only)')
    parser.add_argument('--in-place', '-i', action='store_true', help='Modify files in-place')
    parser.add_argument('--backup', '-b', action='store_true', help='Create .bak backup before modifying')
    parser.add_argument('--output', '-o', help='Output file path (for single file only)')
    parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--no-verify', action='store_true', help='Disable code verification (allow code changes)')
    parser.add_argument('--reference', help='Path to reference file (default: angle_set.h)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}")
        return 1
    
    if args.output and os.path.isdir(args.path):
        print("Error: --output can only be used with a single file")
        return 1
    
    if args.in_place and args.output:
        print("Error: Cannot use both --in-place and --output")
        return 1
    
    # Initialize validator
    print("Initializing validator...")
    reference_file = args.reference or "angle_set.h"
    verify_code = not args.no_verify
    validator = DoxygenValidator(reference_file_path=reference_file, verify_code=verify_code)
    print()
    
    # Find files to process
    files = find_header_files(args.path, args.recursive)
    
    if not files:
        print(f"No header files found in: {args.path}")
        return 1
    
    print(f"Found {len(files)} file(s) to process")
    
    # Process files
    success_count = 0
    fail_count = 0
    
    for file_path in files:
        if process_file(file_path, validator, args):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total files: {len(files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"{'='*80}")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
