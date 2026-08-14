#!/usr/bin/env python3
"""
Generate repository digest with proper UTF-8 encoding.
Fixes cp1252 codec errors on Windows.
"""
import os
import sys
from pathlib import Path

def generate_digest(root_dir, output_file):
    """Walk directory tree and write all file contents to digest."""
    
    # ✅ Écriture en UTF-8 explicite
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("Directory structure:\n")
        
        # Arborescence
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Ignorer .git et __pycache__
            dirnames[:] = [d for d in dirnames if d not in ['.git', '__pycache__', 'node_modules']]
            
            level = dirpath.replace(root_dir, '').count(os.sep)
            indent = '│   ' * level
            out.write(f'{indent}├── {os.path.basename(dirpath)}/\n')
            
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, root_dir)
                
                out.write(f'\n{"=" * 50}\n')
                out.write(f'FILE: {rel_path}\n')
                out.write(f'{"=" * 50}\n')
                
                try:
                    # ✅ Lecture UTF-8 explicite (CORRECTION CLÉ)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        out.write(content)
                        out.write('\n')
                        
                except UnicodeDecodeError as e:
                    # Fichier binaire ou encodage non-UTF-8
                    out.write(f'[BINARY/ENCODED FILE] {e}\n')
                except Exception as e:
                    out.write(f'[ERROR] {e}\n')
    
    print(f'[OK] Digest generated: {output_file}')

if __name__ == '__main__':
    # Arguments : directory et output file
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    output = sys.argv[2] if len(sys.argv) > 2 else 'digest.txt'
    generate_digest(root, output)
