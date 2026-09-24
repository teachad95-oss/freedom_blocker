import subprocess
import sys
import os

def test():
    exe_path = r'"d:\Projects\freedom_blocker\dist\FreedomBlocker.exe"'
    args = [
        'schtasks', '/Create', 
        '/TN', 'TestFreedomList', 
        '/TR', exe_path, 
        '/SC', 'ONLOGON', 
        '/RL', 'HIGHEST', 
        '/F'
    ]
    print(f"Running: {args}")
    result = subprocess.run(args, capture_output=True, text=True)
    print(f"Code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")

if __name__ == "__main__":
    test()
