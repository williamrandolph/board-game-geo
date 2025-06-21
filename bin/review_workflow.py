#!/usr/bin/env python3
"""
Complete review workflow: BGG validation + manual review interface.
"""

import sys
import os
import subprocess

def run_workflow(db_path="data/processed/boardgames.db", validation_limit=None):
    """Run the complete review workflow."""
    
    print("🚀 Starting Board Game Geography Review Workflow")
    print(f"📊 Database: {db_path}")
    print("=" * 60)
    
    # Step 1: Run BGG validation
    print("📋 Step 1: Running BGG validation to auto-approve slam dunks...")
    
    validation_cmd = ["python3", "bin/validate_matches.py", "--db", db_path]
    if validation_limit:
        validation_cmd.extend(["--limit", str(validation_limit)])
    
    try:
        result = subprocess.run(validation_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ BGG validation completed successfully")
            
            # Show summary from validation output
            lines = result.stdout.split('\n')
            summary_started = False
            for line in lines:
                if "VALIDATION SUMMARY" in line:
                    summary_started = True
                if summary_started and line.strip():
                    print(f"  {line}")
                if summary_started and line.strip() == "":
                    break
        else:
            print("❌ BGG validation failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running BGG validation: {e}")
        return False
    
    print("\n" + "=" * 60)
    
    # Step 2: Start manual review interface
    print("📋 Step 2: Starting manual review interface...")
    print("🌐 Opening web interface for remaining matches...")
    
    try:
        # Import and run the manual review server
        sys.path.append('bin')
        from manual_review import start_review_server
        
        start_review_server(db_path)
        
    except KeyboardInterrupt:
        print("\n✅ Review workflow completed!")
    except Exception as e:
        print(f"❌ Error starting manual review: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    validation_limit = None
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            i += 2
        elif arg == "--limit" and i + 1 < len(sys.argv):
            validation_limit = int(sys.argv[i + 1])
            i += 2
        elif arg in ["--help", "-h"]:
            print("Usage: python review_workflow.py [options]")
            print()
            print("Complete workflow for reviewing board game geography matches:")
            print("1. Runs BGG validation to auto-approve obvious matches")
            print("2. Opens manual review interface for remaining matches")
            print()
            print("Options:")
            print("  --db PATH      Database path (default: data/processed/boardgames.db)")
            print("  --limit N      Limit validation to first N matches (for testing)")
            print("  --help         Show this help")
            print()
            print("Example:")
            print("  python review_workflow.py --limit 50  # Review first 50 matches")
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
    
    success = run_workflow(db_path, validation_limit)
    sys.exit(0 if success else 1)