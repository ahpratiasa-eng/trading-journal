"""
Fix ALL indentation issues in trading_journal.py
"""

with open('trading_journal.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track all lines that need fixing - find lines that follow "if/with/for/etc:" and are not indented
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.rstrip('\r\n')
    
    # Check if this line ends with : and is a control statement
    if stripped.endswith(':'):
        trimmed = stripped.lstrip()
        if any(trimmed.startswith(kw) for kw in ['if ', 'else:', 'elif ', 'for ', 'while ', 'with ', 'try:', 'except', 'finally:']):
            parent_indent = len(stripped) - len(trimmed)
            # Check next non-empty line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            
            if j < len(lines):
                next_line = lines[j]
                next_trimmed = next_line.lstrip()
                if next_trimmed:  # Non-empty
                    next_indent = len(next_line) - len(lines[j].lstrip())
                    # Should be indented more than parent
                    if next_indent <= parent_indent:
                        # Fix: add enough spaces
                        needed = parent_indent + 4 - next_indent
                        # Fix all lines in this block until we hit something at parent level or less
                        k = j
                        while k < len(lines):
                            check_line = lines[k]
                            check_stripped = check_line.lstrip()
                            if check_stripped:
                                check_indent = len(check_line) - len(check_stripped)
                                if check_indent <= parent_indent:
                                    # Back to parent level, stop
                                    break
                                # Add needed spaces
                                lines[k] = ' ' * needed + lines[k]
                            k += 1
    
    fixed_lines.append(lines[i])
    i += 1

# Write back
with open('trading_journal.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done!")

# Check syntax
import ast
try:
    with open('trading_journal.py', 'r', encoding='utf-8') as f:
        ast.parse(f.read())
    print("SUCCESS! Syntax is valid!")
except SyntaxError as e:
    print(f"Still has error at line {e.lineno}: {e.msg}")
