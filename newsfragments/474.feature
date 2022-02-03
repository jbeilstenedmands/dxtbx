At upstream request, the installation behaviour in existing installation requirements has been inverted. If you have an existing DIALS install, then for your first reconfigure you require the environment variable ``TBX_INSTALL_PACKAGE_BASE`` to continue using standard python package installation, and avoid getting a second copy of dxtbx package metadata. Alternatively, ``touch build/TBX_INSTALL_PACKAGE_BASE``.
