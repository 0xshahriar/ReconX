#!/usr/bin/env python3
"""
ReconX Termux Fixes
Fix common Termux-specific issues
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class TermuxPatcher:
    """Apply Termux-specific fixes"""
    
    PREFIX = Path("/data/data/com.termux/files/usr")
    HOME = Path("/data/data/com.termux/files/home")
    
    @classmethod
    def is_termux(cls) -> bool:
        """Check if running in Termux"""
        return "TERMUX_VERSION" in os.environ
    
    @classmethod
    def fix_dns(cls):
        """Fix DNS resolution issues"""
        resolv_conf = cls.PREFIX / "etc/resolv.conf"
        
        if resolv_conf.exists():
            print("✓ resolv.conf exists")
            return
        
        print("🔧 Creating resolv.conf...")
        resolv_conf.parent.mkdir(parents=True, exist_ok=True)
        
        with open(resolv_conf, 'w') as f:
            f.write("nameserver 1.1.1.1\n")
            f.write("nameserver 8.8.8.8\n")
            f.write("nameserver 9.9.9.9\n")
        
        print("✓ DNS fixed")
    
    @classmethod
    def fix_permissions(cls):
        """Fix common permission issues"""
        print("🔧 Fixing permissions...")
        
        # Fix storage permission
        if not Path("/sdcard").exists():
            print("  Requesting storage permission...")
            subprocess.run(["termux-setup-storage"], check=False)
        
        # Fix script permissions
        reconx_dir = cls.HOME / "ReconX"
        if reconx_dir.exists():
            scripts_dir = reconx_dir / "scripts"
            if scripts_dir.exists():
                for script in scripts_dir.glob("*.sh"):
                    script.chmod(0o755)
                    print(f"  ✓ {script.name}")
        
        print("✓ Permissions fixed")
    
    @classmethod
    def fix_golang_path(cls):
        """Ensure Go bin is in PATH"""
        bashrc = cls.HOME / ".bashrc"
        
        go_paths = [
            'export GOPATH="$HOME/go"',
            'export PATH="$PATH:$GOPATH/bin"'
        ]
        
        if bashrc.exists():
            content = bashrc.read_text()
            
            with open(bashrc, 'a') as f:
                for path_line in go_paths:
                    if path_line not in content:
                        f.write(f"\n{path_line}\n")
                        print(f"  Added: {path_line}")
        
        print("✓ Go PATH configured")
    
    @classmethod
    def fix_pip_config(cls):
        """Fix pip configuration for Termux"""
        pip_conf_dir = cls.PREFIX / "etc"
        pip_conf_dir.mkdir(parents=True, exist_ok=True)
        
        pip_conf = pip_conf_dir / "pip.conf"
        
        if not pip_conf.exists():
            with open(pip_conf, 'w') as f:
                f.write("[global]\n")
                f.write("no-cache-dir = false\n")
                f.write("disable-pip-version-check = true\n")
            
            print("✓ Pip config created")
    
    @classmethod
    def fix_proot_issues(cls):
        """Fix issues when running in proot/chroot"""
        # Check if we're in proot
        if Path("/proc/1/root").resolve() != Path("/"):
            print("⚠️  Running in container/proot")
            
            # Fix DNS in proot
            cls.fix_dns()
            
            # Ensure /etc/resolv.conf is symlinked correctly
            resolv_link = Path("/etc/resolv.conf")
            if resolv_link.exists() and not resolv_link.is_symlink():
                resolv_link.unlink()
                resolv_link.symlink_to(cls.PREFIX / "etc/resolv.conf")
                print("✓ Fixed resolv.conf symlink")
    
    @classmethod
    def install_termux_api(cls):
        """Install Termux:API if not present"""
        api_commands = [
            "termux-battery-status",
            "termux-notification",
            "termux-wifi-connectioninfo"
        ]
        
        missing = []
        for cmd in api_commands:
            if not shutil.which(cmd):
                missing.append(cmd)
        
        if missing:
            print(f"🔧 Installing Termux:API tools...")
            print(f"  Missing: {', '.join(missing)}")
            print("  Run: pkg install termux-api")
            print("  And install Termux:API app from F-Droid")
    
    @classmethod
    def optimize_for_device(cls):
        """Optimize settings based on device specs"""
        # Check RAM
        try:
            with open("/proc/meminfo") as f:
                mem_total = f.readline()
                total_kb = int(mem_total.split()[1])
                total_gb = total_kb / (1024 * 1024)
                
                print(f"📱 Device RAM: {total_gb:.1f}GB")
                
                if total_gb < 4:
                    print("  ⚠️  Low RAM device detected")
                    print("  Recommendations:")
                    print("    - Use smaller wordlists")
                    print("    - Reduce concurrent scans to 1")
                    print("    - Use gemma3:1b LLM model")
                elif total_gb < 8:
                    print("  ✓ Moderate RAM")
                    print("  Recommendations:")
                    print("    - Use gemma3:4b LLM model")
                    print("    - Enable swap if available")
                else:
                    print("  ✓ Good RAM available")
                    print("  - Can use llama3.1:8b LLM model")
        
        except Exception as e:
            print(f"  ⚠️  Could not detect RAM: {e}")
    
    @classmethod
    def apply_all_fixes(cls):
        """Apply all fixes"""
        if not cls.is_termux():
            print("❌ Not running in Termux")
            return False
        
        print("🔧 ReconX Termux Fixer")
        print("======================")
        print()
        
        cls.fix_dns()
        cls.fix_permissions()
        cls.fix_golang_path()
        cls.fix_pip_config()
        cls.fix_proot_issues()
        cls.install_termux_api()
        cls.optimize_for_device()
        
        print()
        print("======================")
        print("✅ All fixes applied!")
        print()
        print("Please restart Termux or run: source ~/.bashrc")
        
        return True

def main():
    """CLI entry point"""
    if len(sys.argv) > 1:
        fix = sys.argv[1]
        
        if fix == "dns":
            TermuxPatcher.fix_dns()
        elif fix == "perms":
            TermuxPatcher.fix_permissions()
        elif fix == "path":
            TermuxPatcher.fix_golang_path()
        elif fix == "all":
            TermuxPatcher.apply_all_fixes()
        else:
            print(f"Unknown fix: {fix}")
            print("Available: dns, perms, path, all")
    else:
        TermuxPatcher.apply_all_fixes()

if __name__ == "__main__":
    main()
