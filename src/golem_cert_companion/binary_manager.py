import os
import platform
import requests
import tarfile
import zipfile
import tempfile
from pathlib import Path
import stat
import shutil

VERSION = "pre-rel-v0.1.2-rc4"  # Update to your desired version

BINARY_URLS = {
    ('Windows', 'AMD64'): f'https://github.com/golemfactory/golem-certificate/releases/download/{VERSION}/golem-certificate-cli-windows-{VERSION}.zip',
    ('Darwin', 'arm64'): f'https://github.com/golemfactory/golem-certificate/releases/download/{VERSION}/golem-certificate-cli-osx-{VERSION}.tar.gz',
    ('Linux', 'x86_64'): f'https://github.com/golemfactory/golem-certificate/releases/download/{VERSION}/golem-certificate-cli-linux-{VERSION}.tar.gz',
}


class BinaryManager:
    def __init__(self):
        self.binary_path = self._get_binary_path()

    def _get_binary_path(self) -> Path:
        """Get the path where the binary should be stored"""
        home = Path.home()
        base_dir = home / '.golem-cert-manager'
        base_dir.mkdir(exist_ok=True)
        return base_dir / self._get_binary_name()

    def _get_binary_name(self) -> str:
        """Get the platform-specific binary name"""
        system = platform.system()
        return 'golem-certificate-cli.exe' if system == 'Windows' else 'golem-certificate-cli'

    def _get_download_url(self) -> str:
        """Get the correct binary URL for the current platform"""
        system = platform.system()
        machine = platform.machine()
        key = (system, machine)
        print(key)
        if key not in BINARY_URLS:
            raise RuntimeError(f"No binary available for {system} {machine}")

        return BINARY_URLS[key]

    def ensure_binary(self) -> Path:
        """Ensure the binary exists and is executable"""
        if not self.binary_path.exists():
            self._download_and_extract_binary()

        if platform.system() != 'Windows':
            # Make binary executable on Unix-like systems
            current_mode = os.stat(self.binary_path).st_mode
            os.chmod(self.binary_path, current_mode | stat.S_IXUSR)

        return self.binary_path

    def _download_and_extract_binary(self):
        """Download and extract the appropriate binary"""
        url = self._get_download_url()
        system = platform.system()

        print(f"Downloading certificate CLI binary from {url}...")

        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Download the archive
            archive_path = temp_dir_path / \
                ('archive.zip' if system == 'Windows' else 'archive.tar.gz')
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extract the binary
            if system == 'Windows':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir_path)
            else:
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(temp_dir_path)

            # Find and move the binary
            binary_name = self._get_binary_name()
            extracted_binary = None

            # Search for the binary in the extracted files
            for root, _, files in os.walk(temp_dir_path):
                for file in files:
                    if file == binary_name:
                        extracted_binary = Path(root) / file
                        break

            if not extracted_binary:
                raise RuntimeError(
                    f"Could not find binary {binary_name} in extracted files")

            # Move the binary to its final location
            shutil.move(str(extracted_binary), str(self.binary_path))

        print(f"Binary extracted to {self.binary_path}")