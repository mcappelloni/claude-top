#!/usr/bin/env node

/**
 * claude-top - Terminal-based monitoring tool for Claude CLI instances
 * 
 * This is a Node.js wrapper that executes the Python claude-top script
 * with proper environment setup and dependency checking.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Colors for terminal output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

// Check if Python 3 is installed
function checkPython() {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const checkCmd = spawn(pythonCmd, ['--version']);
    
    checkCmd.on('error', () => resolve(false));
    checkCmd.on('exit', (code) => resolve(code === 0));
  });
}

// Check if psutil is installed
function checkPsutil() {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const checkCmd = spawn(pythonCmd, ['-c', 'import psutil']);
    
    checkCmd.on('error', () => resolve(false));
    checkCmd.on('exit', (code) => resolve(code === 0));
  });
}

// Get virtual environment path
function getVenvPath() {
  const claudeTopDir = path.join(__dirname, '..');
  const venvPath = path.join(claudeTopDir, '.venv');
  return fs.existsSync(venvPath) ? venvPath : null;
}

// Create virtual environment
function createVenv() {
  console.log(`${colors.yellow}Creating Python virtual environment...${colors.reset}`);
  
  return new Promise((resolve, reject) => {
    const claudeTopDir = path.join(__dirname, '..');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const venvCmd = spawn(pythonCmd, ['-m', 'venv', '.venv'], { cwd: claudeTopDir });
    
    venvCmd.on('error', (err) => {
      console.error(`${colors.red}Failed to create virtual environment: ${err.message}${colors.reset}`);
      reject(err);
    });
    
    venvCmd.on('exit', (code) => {
      if (code === 0) {
        console.log(`${colors.green}✓ Virtual environment created${colors.reset}`);
        resolve();
      } else {
        reject(new Error(`venv creation failed with code ${code}`));
      }
    });
  });
}

// Install psutil in virtual environment
function installPsutilInVenv(venvPath) {
  console.log(`${colors.yellow}Installing psutil in virtual environment...${colors.reset}`);
  
  return new Promise((resolve, reject) => {
    const pipPath = process.platform === 'win32' 
      ? path.join(venvPath, 'Scripts', 'pip')
      : path.join(venvPath, 'bin', 'pip');
    
    const pipCmd = spawn(pipPath, ['install', 'psutil']);
    
    pipCmd.stdout.on('data', (data) => process.stdout.write(data));
    pipCmd.stderr.on('data', (data) => process.stderr.write(data));
    
    pipCmd.on('error', (err) => {
      console.error(`${colors.red}Failed to install psutil: ${err.message}${colors.reset}`);
      reject(err);
    });
    
    pipCmd.on('exit', (code) => {
      if (code === 0) {
        console.log(`${colors.green}✓ psutil installed successfully${colors.reset}`);
        resolve();
      } else {
        reject(new Error(`pip install failed with code ${code}`));
      }
    });
  });
}

// Main function
async function main() {
  console.log(`${colors.blue}claude-top - Claude CLI Monitor${colors.reset}`);
  
  // Check Python installation
  const hasPython = await checkPython();
  if (!hasPython) {
    console.error(`${colors.red}Error: Python 3 is required but not found.${colors.reset}`);
    console.error('Please install Python 3 from https://www.python.org/downloads/');
    process.exit(1);
  }
  
  // Find the claude-top Python script
  const scriptPath = path.join(__dirname, '..', 'claude-top');
  
  if (!fs.existsSync(scriptPath)) {
    console.error(`${colors.red}Error: claude-top script not found at ${scriptPath}${colors.reset}`);
    process.exit(1);
  }
  
  // Check for virtual environment
  let venvPath = getVenvPath();
  let pythonExe;
  
  if (venvPath) {
    // Use Python from virtual environment
    pythonExe = process.platform === 'win32' 
      ? path.join(venvPath, 'Scripts', 'python.exe')
      : path.join(venvPath, 'bin', 'python');
  } else {
    // Try to use system Python and check for psutil
    const hasPsutil = await checkPsutil();
    if (!hasPsutil) {
      console.log(`${colors.yellow}Setting up Python environment...${colors.reset}`);
      
      try {
        // Create virtual environment
        await createVenv();
        venvPath = getVenvPath();
        
        // Install psutil
        await installPsutilInVenv(venvPath);
        
        pythonExe = process.platform === 'win32' 
          ? path.join(venvPath, 'Scripts', 'python.exe')
          : path.join(venvPath, 'bin', 'python');
      } catch (err) {
        console.error(`${colors.red}Failed to set up Python environment.${colors.reset}`);
        console.error('Please install psutil manually:');
        console.error('  python3 -m venv .venv');
        console.error('  source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate');
        console.error('  pip install psutil');
        process.exit(1);
      }
    } else {
      // System Python has psutil
      pythonExe = process.platform === 'win32' ? 'python' : 'python3';
    }
  }
  
  // Run claude-top with passed arguments
  const args = [scriptPath, ...process.argv.slice(2)];
  
  const claudeTop = spawn(pythonExe, args, {
    stdio: 'inherit',
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });
  
  // Handle process termination
  claudeTop.on('error', (err) => {
    console.error(`${colors.red}Error running claude-top: ${err.message}${colors.reset}`);
    process.exit(1);
  });
  
  claudeTop.on('exit', (code) => {
    process.exit(code || 0);
  });
  
  // Forward signals to the Python process
  ['SIGINT', 'SIGTERM'].forEach(signal => {
    process.on(signal, () => {
      claudeTop.kill(signal);
    });
  });
}

// Run the main function
main().catch((err) => {
  console.error(`${colors.red}Unexpected error: ${err.message}${colors.reset}`);
  process.exit(1);
});