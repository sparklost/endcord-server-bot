import glob
import os
import shutil
import stat
import subprocess
import sys

PACKAGES = ["apsw==3.53.3.1", "psycopg==3.3.4"]
TERMUX_PACKAGES = ["apsw"]
SCRIPTS = ["manage-endcord.sh", "ssh-ngrok.sh", "ssh-tor.sh"]


def install_packages_termux(packages):
    """Install specified packages in extension dir, for termux"""
    for package in packages:
        if not shutil.which(package):
            subprocess.run(["pkg", "i", f"python-{package}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        current_dir = os.getcwd()
        system_dir = glob.glob(os.path.expandvars("$PREFIX/lib/python*/site-packages"))[0]
        shutil.copytree(os.path.join(system_dir, package), os.path.join(current_dir, package))


def install_packages(libraries):
    """Install specified packages in extension dir"""
    subprocess.run(["python", "-m", "venv", "env"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for lib in libraries:
        if lib.startswith("psycopg") and sys.platform =="android" and shutil.which("termux-backup") and shutil.which("clang"):
            lib = lib.replace("psycopg", "psycopg[c]")   # noqa
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
    for lib in libraries:
        if lib.startswith("psycopg") and sys.platform =="android" and shutil.which("termux-backup") and shutil.which("clang"):
            shutil.move(os.path.join(temp_dir, "psycopg_c"), os.path.join(current_dir, "psycopg_c"))
        lib_name = lib.split("<")[0].split(">")[0].split("=")[0]
        shutil.move(os.path.join(temp_dir, lib_name), os.path.join(current_dir, lib_name))
    shutil.rmtree(temp_dir)
    shutil.rmtree(os.path.join(current_dir, "env"))


def install_script(filename):
    """Install .sh script from the current directory into the user-level bin directory"""
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"File '{filename}' not found in current directory.")

    if "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ:
        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        target_dir = os.path.join(prefix, "bin")
    else:
        target_dir = os.path.expanduser("~/.local/bin")
    os.makedirs(target_dir, exist_ok=True)
    dest_path = os.path.join(target_dir, os.path.basename(filename)[:-3])
    shutil.copy2(filename, dest_path)
    current_mode = os.stat(dest_path).st_mode
    executable_mode = current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    os.chmod(dest_path, executable_mode)


def main():
    """Setup environment"""
    if "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ:
        install_packages_termux(TERMUX_PACKAGES)
        install_packages([x for x in PACKAGES if not any(x.startswith(y) for y in TERMUX_PACKAGES)])
        return
    install_packages(PACKAGES)
    for script in SCRIPTS:
        install_script(script)


if __name__ == "__main__":
    main()
