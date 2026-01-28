
import sys
import os
import re

# Mock settings
class Settings:
    ai_scientist_root = "/home/guv/AI_Scientist"

sys.modules['backend.app.settings'] = type('module', (), {'settings': Settings()})

# Import the target function - manually defining it to avoid import issues if possible, 
# or just import if path is correct.
# Let's try to import directly first.
sys.path.append("/home/guv/AI_Scientist/AI_Scientist_WebAPP")

try:
    from backend.app.prompts import load_baseline_system_messages, _SYSTEM_MESSAGE_RE
    
    print(f"Regex pattern: {_SYSTEM_MESSAGE_RE.pattern}")
    
    messages = load_baseline_system_messages()
    print(f"Loaded {len(messages)} messages:")
    for k, v in messages.items():
        print(f" - {k}: {len(v)} chars")
        
    # Test specific file content if empty
    if not messages:
        target = "/home/guv/AI_Scientist/prompts/system_PI.py"
        if os.path.exists(target):
            with open(target, 'r') as f:
                content = f.read()
            print(f"\nContent of {target} (first 500 chars):")
            print(content[:500])
            
            match = _SYSTEM_MESSAGE_RE.search(content)
            if match:
                print("\nRegex MATCHED!")
                print(f"Group 'body': {match.group('body')[:50]}...")
            else:
                print("\nRegex NOT MATCHED!")
        else:
            print(f"File {target} not found")

except Exception as e:
    print(f"Error: {e}")
