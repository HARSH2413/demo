import os

exclude_dirs = {'node_modules', '.git', 'venv', '__pycache__', '.next', '.vscode', 'dist', 'build'}
exclude_exts = {'.jpg', '.png', '.pyc', '.pdf', '.docx', '.lock', '.ico', '.svg', '.env', '.sqlite3'}

def generate_tree(dir_path, prefix=""):
    try:
        items = sorted([item for item in os.listdir(dir_path) if item not in exclude_dirs])
    except PermissionError:
        return ""
    tree_str = ""
    for i, item in enumerate(items):
        path = os.path.join(dir_path, item)
        is_last = (i == len(items) - 1)
        tree_str += prefix + ("└── " if is_last else "├── ") + item + "\n"
        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            tree_str += generate_tree(path, prefix + extension)
    return tree_str

with open('all_codes.md', 'w', encoding='utf-8') as out_f:
    out_f.write("# Project Folder Structure\n\n")
    out_f.write("```\n")
    out_f.write(".\n")
    out_f.write(generate_tree('.'))
    out_f.write("```\n\n")
    
    out_f.write("# All Project Code\n\n")
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        dirs.sort()
        files.sort()
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in exclude_exts or 'lock' in file or file == 'all_codes.md' or file == 'generate_doc.py':
                continue
                
            filepath = os.path.join(root, file)
            if filepath.startswith('./'):
                filepath = filepath[2:]
                
            out_f.write(f"## File: `{filepath}`\n\n")
            try:
                with open(filepath, 'r', encoding='utf-8') as in_f:
                    content = in_f.read()
                    out_f.write("```" + (ext[1:] if ext else "") + "\n")
                    out_f.write(content)
                    if content and not content.endswith('\n'):
                        out_f.write("\n")
                    out_f.write("```\n\n")
            except Exception as e:
                out_f.write(f"*(Could not read file: {e})*\n\n")

print("Generated all_codes.md with folder structure successfully.")
