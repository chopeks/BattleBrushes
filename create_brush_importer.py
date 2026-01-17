#!/usr/bin/env python3
"""
Create a GUI brush file importer for seamless Tiled integration

This creates a simple GUI application that:
1. Provides a file dialog to select .brush files
2. Automatically converts them using our working converter
3. Opens the result in Tiled
4. Can be launched from desktop or file manager

True UI-only workflow for artists!
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import sys
from pathlib import Path

class BrushImporter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Battle Brothers Brush Importer")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Battle Brothers Brush Importer", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Description
        desc_text = """Import Battle Brothers .brush files directly into Tiled!
        
This tool converts .brush files to Tiled's native .tsx format,
preserving all metadata and extracting individual sprites.

Perfect for UI-only workflow - no command line needed!"""
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify=tk.LEFT, 
                              wraplength=450, font=('Arial', 10))
        desc_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Import button
        import_btn = ttk.Button(main_frame, text="📁 Import Brush File", 
                               command=self.import_brush, style='Accent.TButton')
        import_btn.grid(row=2, column=0, padx=(0, 10), pady=10, sticky=tk.W+tk.E)
        
        # Open Tiled button
        tiled_btn = ttk.Button(main_frame, text="🎨 Open Tiled", 
                              command=self.open_tiled)
        tiled_btn.grid(row=2, column=1, padx=(10, 0), pady=10, sticky=tk.W+tk.E)
        
        # Progress bar (initially hidden)
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky=tk.W+tk.E, pady=10)
        self.progress.grid_remove()  # Hide initially
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to import brush files", 
                                     font=('Arial', 9), foreground='gray')
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def update_status(self, message, color='black'):
        self.status_label.config(text=message, foreground=color)
        self.root.update()
        
    def import_brush(self):
        # File dialog to select brush file
        brush_file = filedialog.askopenfilename(
            title="Select Battle Brothers Brush File",
            filetypes=[
                ("Battle Brothers Brush files", "*.brush"),
                ("All files", "*.*")
            ]
        )
        
        if not brush_file:
            return
            
        self.update_status("Converting brush file...", 'blue')
        self.progress.grid()  # Show progress bar
        self.progress.start()
        
        try:
            # Find the converter script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            converter_script = os.path.join(script_dir, "brush_to_tiled.sh")
            
            if not os.path.exists(converter_script):
                # Look in common locations
                possible_locations = [
                    os.path.expanduser("~/.local/share/tiled/plugins/brush_to_tiled.sh"),
                    "./brush_to_tiled.sh"
                ]
                
                converter_script = None
                for location in possible_locations:
                    if os.path.exists(location):
                        converter_script = location
                        break
                
                if not converter_script:
                    raise FileNotFoundError("Converter script not found")
            
            # Generate output filename
            brush_path = Path(brush_file)
            output_file = brush_path.parent / f"{brush_path.stem}_imported.tsx"
            
            # Run the converter
            result = subprocess.run(
                [converter_script, brush_file, str(output_file)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.progress.stop()
            self.progress.grid_remove()
            
            if result.returncode == 0:
                self.update_status("✅ Conversion successful!", 'green')
                
                # Ask if user wants to open in Tiled
                if messagebox.askyesno("Success!", 
                                     f"Successfully imported brush file!\n\n"
                                     f"Converted to: {output_file.name}\n\n"
                                     f"Open in Tiled now?"):
                    self.open_file_in_tiled(str(output_file))
                    
            else:
                raise Exception(f"Converter failed with exit code {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.progress.stop()
            self.progress.grid_remove()
            self.update_status("❌ Conversion timed out", 'red')
            messagebox.showerror("Error", "Conversion took too long and was cancelled.")
            
        except Exception as e:
            self.progress.stop()
            self.progress.grid_remove()
            self.update_status("❌ Conversion failed", 'red')
            messagebox.showerror("Error", f"Failed to convert brush file:\n{str(e)}")
    
    def open_tiled(self):
        """Open Tiled application"""
        try:
            subprocess.Popen(['tiled'], start_new_session=True)
            self.update_status("Opened Tiled", 'green')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Tiled:\n{str(e)}")
    
    def open_file_in_tiled(self, file_path):
        """Open specific file in Tiled"""
        try:
            subprocess.Popen(['tiled', file_path], start_new_session=True)
            self.update_status(f"Opened {os.path.basename(file_path)} in Tiled", 'green')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file in Tiled:\n{str(e)}")
    
    def run(self):
        self.root.mainloop()

def create_desktop_shortcut():
    """Create a desktop shortcut for easy access"""
    desktop = os.path.expanduser("~/Desktop")
    if not os.path.exists(desktop):
        desktop = os.path.expanduser("~/")
    
    shortcut_content = f"""[Desktop Entry]
Name=Battle Brothers Brush Importer
Comment=Import Battle Brothers .brush files into Tiled
Exec=python3 "{os.path.abspath(__file__)}"
Icon=applications-games
Terminal=false
Type=Application
Categories=Graphics;2DGraphics;
"""
    
    shortcut_path = os.path.join(desktop, "BrushImporter.desktop")
    
    try:
        with open(shortcut_path, 'w') as f:
            f.write(shortcut_content)
        
        # Make executable
        os.chmod(shortcut_path, 0o755)
        print(f"Created desktop shortcut: {shortcut_path}")
        
    except Exception as e:
        print(f"Failed to create desktop shortcut: {e}")

if __name__ == "__main__":
    # Check if we should create desktop shortcut
    if len(sys.argv) > 1 and sys.argv[1] == "--create-shortcut":
        create_desktop_shortcut()
        sys.exit(0)
    
    # Check dependencies
    try:
        import tkinter
    except ImportError:
        print("Error: tkinter not found. Install with: sudo apt install python3-tk")
        sys.exit(1)
    
    # Run the GUI
    app = BrushImporter()
    app.run()