"""Single release identity for runtime and native packaging."""
VERSION = "0.4.9rc2"
BUNDLE_VERSION = "0.4.9"

if __name__ == "__main__":
    import sys
    print(BUNDLE_VERSION if "--bundle" in sys.argv else VERSION)
