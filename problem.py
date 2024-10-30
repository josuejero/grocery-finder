import os
import shutil
import subprocess
import sys

import pyperclip

output_file_path = "all_code.txt"
MAX_FILE_SIZE = 500 * 1024 * 1024

try:
    with open(output_file_path, "w") as file:
        pass
except IOError as e:
    print(f"Error initializing '{output_file_path}': {e}")
    sys.exit(1)


def get_multiline_input(prompt):
    print(prompt)
    print("Type 'END' on a new line to finish.")
    lines = []
    try:
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
    except KeyboardInterrupt:
        print("\nInput interrupted by user.")
        sys.exit(1)
    except EOFError:
        print("\nEnd of file reached unexpectedly.")
        sys.exit(1)
    return "\n".join(lines)


problem_message = get_multiline_input("Enter the problem with the code:")

try:
    with open(output_file_path, "a") as file:
        file.write(f"{problem_message}\n\n")
        file.write(
            "This is a website I am working on. "
            "Please analyze the project structure, errors, and code carefully:\n\n"
        )
except IOError as e:
    print(f"Error writing to '{output_file_path}': {e}")
    sys.exit(1)

if shutil.which("tree") is None:
    print("Error: 'tree' command is not available. Please install it and try again.")
    sys.exit(1)

try:
    tree_output = subprocess.run(
        ["tree", "-I", ".next|node_modules|venv|.git"],
        capture_output=True,
        text=True,
        check=True,
    )
    with open(output_file_path, "a") as file:
        file.write(tree_output.stdout)
        file.write("\n")
except subprocess.CalledProcessError as e:
    print(f"Error executing 'tree' command: {e}")
    sys.exit(1)
except IOError as e:
    print(f"Error writing to '{output_file_path}': {e}")
    sys.exit(1)

exclude_dirs = {"node_modules", ".next", "venv", ".git", "__pycache__"}
exclude_files = {"package-lock.json", output_file_path}

allowed_extensions = {
    ".md",
    ".json",
    ".mjs",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".css",
    ".module.css",
    ".scss",
    ".txt",
    ".yml",
    ".yaml",
    ".tf",
    ".py",
    ".env",
    ".ini",
    ".cjg",
    ".gitignore",
    ".log",
    "",
}
allowed_filenames = {"Dockerfile"}

try:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file in exclude_files:
                continue
            file_path_full = os.path.join(root, file)
            ext = os.path.splitext(file)[1]
            if ext in allowed_extensions or file in allowed_filenames:
                try:
                    with open(file_path_full, "r") as f:
                        content = f.read()
                    relative_path = os.path.relpath(file_path_full, ".")
                    with open(output_file_path, "a") as outfile:
                        outfile.write("\n")
                        outfile.write("=" * 80 + "\n")
                        outfile.write(f"File: {relative_path}\n")
                        outfile.write("=" * 80 + "\n\n")
                        outfile.write(content)
                        outfile.write("\n")
                except Exception as e:
                    print(f"Error reading file '{file_path_full}': {e}")
except Exception as e:
    print(f"Error during directory traversal: {e}")
    sys.exit(1)

try:
    file_size = os.path.getsize(output_file_path)
except OSError as e:
    print(f"Error getting size of '{output_file_path}': {e}")
    sys.exit(1)

if file_size > MAX_FILE_SIZE:
    mb_size = file_size / (1024 * 1024)
    print(f"Warning: The file '{output_file_path}' exceeds 500 MB ({mb_size:.2f} MB).")
    print("Copying such a large amount of data to the clipboard may cause issues.")
    user_choice = (
        input("Do you want to proceed with copying to clipboard? (y/N): ")
        .strip()
        .lower()
    )
    if user_choice != "y":
        print("Skipping copying to clipboard.")
        print(f"All steps completed, '{output_file_path}' has been updated.")
        sys.exit(0)
    else:
        print("Proceeding to copy to clipboard. This may take some time.")
else:
    mb_size = file_size / (1024 * 1024)
    print(f"The file size of '{output_file_path}' is {mb_size:.2f} MB.")

try:
    with open(output_file_path, "r") as file:
        file_content = file.read()
except IOError as e:
    print(f"Error reading from '{output_file_path}': {e}")
    sys.exit(1)

try:
    pyperclip.copy(file_content)
except pyperclip.PyperclipException as e:
    print(f"Error copying content to clipboard: {e}")
    print("Proceeding without copying to clipboard.")
except MemoryError:
    print("MemoryError: The file is too large to copy to the clipboard.")
    print("Proceeding without copying to clipboard.")

print(f"All steps completed, '{output_file_path}' has been updated.")
print("Its contents have been copied to the clipboard.")
