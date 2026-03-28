import os
import shutil
import subprocess

LIBRARIES = (
    "apsw",
    #"psycopg",
)


def main():
    """Setup environment"""
    subprocess.run(["virtualenv", "env"], check=True)
    subprocess.run(["./env/bin/python", "-m", "pip", "install", "--target=temp", "apsw"], check=True)
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
