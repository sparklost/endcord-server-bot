import glob
import os
import shutil
import subprocess
import sys

LIBRARIES = (
    "apsw",
    "psycopg",
)


def termux_install_apsw():
    """Setup apsw on termux"""
    lib = "apsw"
    if not shutil.which("apsw"):
        subprocess.run(["pkg", "i", f"python-{lib}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    current_dir = os.getcwd()
    system_dir = glob.glob(os.path.expandvars("$PREFIX/lib/python*/site-packages"))[0]
    shutil.copytree(os.path.join(system_dir, lib), os.path.join(current_dir, lib))


def main():
    """Setup environment"""
    if sys.platform =="android" and shutil.which("termux-backup"):
        termux_install_apsw()
        return
    subprocess.run(["virtualenv", "env"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for lib in LIBRARIES:
        subprocess.run(
            ["./env/bin/python", "-m", "pip", "install", "--target=temp", lib],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, "temp")
    if not os.path.exists(temp_dir):
        return
    for lib in LIBRARIES:
         shutil.move(os.path.join(temp_dir, lib), os.path.join(current_dir, lib))
    shutil.rmtree(temp_dir)
    shutil.rmtree(os.path.join(current_dir, "env"))


if __name__ == "__main__":
    main()
