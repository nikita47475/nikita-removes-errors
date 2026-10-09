TARGETS = {
    "windows": ["Windows 7", "Windows 8", "Windows 9 (not an official Microsoft release; compatibility label)", "Windows 10", "Windows 11"],
    "linux": ["Linux legacy", "Linux LTS/older", "Linux current", "Linux newest"],
    "macos": ["macOS 10.7+ legacy", "macOS 10.12+", "macOS 11+", "macOS current"],
}


def describe_platforms():
    return TARGETS
