# Import dependencies and check if they are installed
try:
    import PIL
    import tqdm
    import reportlab
except ImportError as e:
    print(e)
    print("Please install dependencies. Run the following command.")
    print()
    print("pip install -r requirements.txt")
    exit(1)

# Check if GhostScript is installed
try:
    import subprocess
    subprocess.run(["gs", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
    print("Please install GhostScript. Run the following command.")
    print()
    print("Windows: winget install ghostscript")
    print("Mac: brew install ghostscript")
    exit(1)