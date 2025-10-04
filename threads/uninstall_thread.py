import subprocess
import psutil
import os
from PyQt6.QtCore import QThread, pyqtSignal

class UninstallThread(QThread):
    progress = pyqtSignal(int, str, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    silent_failed = pyqtSignal(dict)

    def __init__(self, programs, silent):
        super().__init__()
        self.programs = programs
        self.silent = silent
        self.current_process = None
        self.uninstalled_programs = []

    def run(self):
        for i, program in enumerate(self.programs):
            try:
                self.progress.emit(i, f"Uninstalling {program['name']}...", "running")
                
                if not self._validate_uninstall_string(program):
                    self.progress.emit(i + 1, f"Invalid uninstall string for {program['name']}", "error")
                    continue
                
                if self.silent:
                    success = self._run_silent_uninstall(program)
                    if not success:
                        self.progress.emit(i + 1, f"Silent uninstall failed for {program['name']}, trying interactive...", "running")
                        success = self._run_interactive_uninstall(program)
                else:
                    success = self._run_interactive_uninstall(program)
                
                if success:
                    self.progress.emit(i + 1, f"{program['name']} successfully uninstalled", "success")
                    self.uninstalled_programs.append(program)
                else:
                    self.progress.emit(i + 1, f"Failed to uninstall {program['name']}", "error")
                    
            except subprocess.TimeoutExpired:
                self.silent_failed.emit(program)
            except Exception as e:
                self.error.emit(f"Error uninstalling {program['name']}: {str(e)}")
        self.finished.emit()

    def _validate_uninstall_string(self, program):
        uninstall_string = program.get('uninstall_string', '')
        if not uninstall_string:
            return False
        
        if uninstall_string.startswith('"'):
            exe_path = uninstall_string.split('"')[1]
        else:
            exe_path = uninstall_string.split()[0]
        
        if exe_path.startswith('MsiExec.exe') or exe_path.startswith('msiexec.exe'):
            return True
        
        if exe_path.startswith('{') and exe_path.endswith('}'):
            return True
        
        return os.path.exists(exe_path)

    def _run_silent_uninstall(self, program):
        try:
            uninstall_string = program['uninstall_string']
            
            if 'msiexec' in uninstall_string.lower():
                if '/I' in uninstall_string:
                    cmd = uninstall_string.replace('/I', '/X') + ' /quiet /norestart'
                else:
                    cmd = uninstall_string + ' /quiet /norestart'
            else:
                if '/S' in uninstall_string or '/s' in uninstall_string:
                    cmd = uninstall_string
                else:
                    cmd = f"{uninstall_string} /S"
            
            self.current_process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            return_code = self.current_process.wait(timeout=300)
            
            if return_code == 0:
                return True
            elif return_code == 1602:
                self.silent_failed.emit(program)
                return False
            else:
                self.silent_failed.emit(program)
                return False
                
        except subprocess.TimeoutExpired:
            if self.current_process:
                self.current_process.kill()
            self.silent_failed.emit(program)
            return False

    def _run_interactive_uninstall(self, program):
        try:
            self.current_process = subprocess.Popen(
                program['uninstall_string'], 
                shell=True
            )
            
            while self.current_process.poll() is None:
                if self.check_child_processes(self.current_process.pid):
                    QThread.msleep(100)
                else:
                    break
            
            return self.current_process.returncode == 0
        except Exception:
            return False

    def check_child_processes(self, parent_pid):
        try:
            parent = psutil.Process(parent_pid)
            children = parent.children(recursive=True)
            return len(children) > 0
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
