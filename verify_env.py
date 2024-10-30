from pathlib import Path


def verify_env_file():
    env_path = Path(".env")
    if not env_path.exists():
        print("Error: .env file not found")
        return

    with open(env_path, "rb") as f:
        content = f.read()

    if content.startswith(b"\xef\xbb\xbf"):
        print("Warning: .env file contains BOM marker")

    print(f"File encoding: {content.decode('utf-8', 'ignore').encode('utf-8')}")

    print("\nRaw contents:")
    print(content)

    print("\nDecoded contents:")
    try:
        decoded = content.decode("utf-8")
        for line_num, line in enumerate(decoded.splitlines(), 1):
            print(f"{line_num:3d}: {line}")
    except UnicodeDecodeError as e:
        print(f"Error decoding file: {e}")


if __name__ == "__main__":
    verify_env_file()
