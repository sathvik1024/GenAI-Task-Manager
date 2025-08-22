#!/usr/bin/env python3
"""
Setup script for GenAI Task Manager
Automates the installation and configuration process
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None, check=True):
    """Run a shell command and return the result"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return None

def check_requirements():
    """Check if required software is installed"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check Node.js
    node_result = run_command("node --version", check=False)
    if not node_result or node_result.returncode != 0:
        print("❌ Node.js is required. Please install from https://nodejs.org/")
        return False
    print(f"✅ Node.js {node_result.stdout.strip()}")
    
    # Check npm
    npm_result = run_command("npm --version", check=False)
    if not npm_result or npm_result.returncode != 0:
        print("❌ npm is required")
        return False
    print(f"✅ npm {npm_result.stdout.strip()}")
    
    return True

def setup_backend():
    """Setup the Flask backend"""
    print("\n🐍 Setting up backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False
    
    # Create virtual environment
    print("Creating virtual environment...")
    venv_command = "python -m venv venv"
    if sys.platform == "win32":
        activate_command = "venv\\Scripts\\activate"
        pip_command = "venv\\Scripts\\pip"
    else:
        activate_command = "source venv/bin/activate"
        pip_command = "venv/bin/pip"
    
    if not run_command(venv_command, cwd=backend_dir):
        return False
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    if not run_command(f"{pip_command} install -r requirements.txt", cwd=backend_dir):
        return False
    
    # Create .env file if it doesn't exist
    env_file = backend_dir / ".env"
    env_example = backend_dir / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file...")
        shutil.copy(env_example, env_file)
        print("⚠️  Please edit backend/.env and add your OpenAI API key")
    
    print("✅ Backend setup complete")
    return True

def setup_frontend():
    """Setup the React frontend"""
    print("\n⚛️  Setting up frontend...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    # Install Node.js dependencies
    print("Installing Node.js dependencies...")
    if not run_command("npm install", cwd=frontend_dir):
        return False
    
    print("✅ Frontend setup complete")
    return True

def create_start_scripts():
    """Create convenient start scripts"""
    print("\n📝 Creating start scripts...")
    
    # Backend start script
    if sys.platform == "win32":
        backend_script = """@echo off
cd backend
call venv\\Scripts\\activate
python app.py
"""
        with open("start_backend.bat", "w") as f:
            f.write(backend_script)
        
        frontend_script = """@echo off
cd frontend
npm start
"""
        with open("start_frontend.bat", "w") as f:
            f.write(frontend_script)
            
        print("✅ Created start_backend.bat and start_frontend.bat")
    else:
        backend_script = """#!/bin/bash
cd backend
source venv/bin/activate
python app.py
"""
        with open("start_backend.sh", "w") as f:
            f.write(backend_script)
        os.chmod("start_backend.sh", 0o755)
        
        frontend_script = """#!/bin/bash
cd frontend
npm start
"""
        with open("start_frontend.sh", "w") as f:
            f.write(frontend_script)
        os.chmod("start_frontend.sh", 0o755)
        
        print("✅ Created start_backend.sh and start_frontend.sh")

def print_next_steps():
    """Print instructions for next steps"""
    print("\n🎉 Setup complete! Next steps:")
    print("\n1. Configure your OpenAI API key:")
    print("   - Edit backend/.env")
    print("   - Add your OpenAI API key: OPENAI_API_KEY=sk-your-key-here")
    print("   - Get your key from: https://platform.openai.com/api-keys")
    
    print("\n2. Start the application:")
    if sys.platform == "win32":
        print("   Backend:  double-click start_backend.bat")
        print("   Frontend: double-click start_frontend.bat")
    else:
        print("   Backend:  ./start_backend.sh")
        print("   Frontend: ./start_frontend.sh")
    
    print("\n3. Access the application:")
    print("   - Frontend: http://localhost:3000")
    print("   - Backend API: http://localhost:5000")
    
    print("\n4. Create your first account and start managing tasks!")
    print("\n📚 For more information, see README.md")

def main():
    """Main setup function"""
    print("🚀 GenAI Task Manager Setup")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Setup failed: Missing requirements")
        sys.exit(1)
    
    # Setup backend
    if not setup_backend():
        print("\n❌ Setup failed: Backend setup error")
        sys.exit(1)
    
    # Setup frontend
    if not setup_frontend():
        print("\n❌ Setup failed: Frontend setup error")
        sys.exit(1)
    
    # Create start scripts
    create_start_scripts()
    
    # Print next steps
    print_next_steps()
    
    print("\n✅ Setup completed successfully!")

if __name__ == "__main__":
    main()
