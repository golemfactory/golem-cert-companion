from .binary_manager import BinaryManager
from colorama import init, Fore, Style
from dateutil import tz
from datetime import datetime, timedelta
import os
import json
import subprocess
from urllib.parse import urlparse
import sys
from .templates import DEFAULT_NODE_DESCRIPTOR, DEFAULT_ROOT_CERT_TEMPLATE


# Initialize colorama for cross-platform colored output
init()


class CertificateManager:
    def __init__(self):
        self.validity_period = None
        self.urls = None
        self.outbound_mode = None
        self.node_id = None
        self.display_name = None
        self.email = None
        self.public_key_data = None
        self.binary_manager = BinaryManager()
        self.binary_path = self.binary_manager.ensure_binary()
        self.ensure_template_files()

    def ensure_template_files(self):
        """Ensure template files exist, create them if they don't"""
        if not os.path.exists("node-descriptor.json"):
            with open("node-descriptor.json", 'w') as f:
                json.dump(DEFAULT_NODE_DESCRIPTOR, f, indent=2)
            print(
                f"{Fore.GREEN}Created default node-descriptor.json{Style.RESET_ALL}")

        if not os.path.exists("root-cert-template.json"):
            with open("root-cert-template.json", 'w') as f:
                json.dump(DEFAULT_ROOT_CERT_TEMPLATE, f, indent=2)
            print(
                f"{Fore.GREEN}Created default root-cert-template.json{Style.RESET_ALL}")

    def is_valid_eth_address(self, address):
        """Validates if the string is a 42-character Ethereum hex address starting with 0x"""
        return bool(address and isinstance(address, str) and
                    len(address) == 42 and
                    address.startswith('0x') and
                    all(c in '0123456789abcdefABCDEF' for c in address[2:]))

    def run_command(self, args, shell=False):
        """Runs a shell command and returns the output, or exits on error."""
        command = [str(self.binary_path)] + args
        try:
            process = subprocess.run(
                command, capture_output=True, text=True, shell=shell, check=True)
            return process.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(
                f"{Fore.RED}  - Error: Command failed with error code {e.returncode}:\n{e.stderr}{Style.RESET_ALL}")
            sys.exit(1)
        except FileNotFoundError:
            print(
                f"{Fore.RED}  - Error: Command not found: {command[0]}. Is it installed and in your PATH?{Style.RESET_ALL}")
            sys.exit(1)

    def update_json_file(self, filepath, update_function):
        """Reads a JSON file, applies an update function, and writes it back."""
        try:
            # If file doesn't exist, use default template
            if not os.path.exists(filepath):
                data = DEFAULT_NODE_DESCRIPTOR if filepath == "node-descriptor.json" else DEFAULT_ROOT_CERT_TEMPLATE
            else:
                with open(filepath, 'r') as f:
                    data = json.load(f)

            updated_data = update_function(data)
            with open(filepath, 'w') as f:
                json.dump(updated_data, f, indent=2)
        except json.JSONDecodeError:
            print(
                f"{Fore.RED}  - Error: Invalid JSON format in file: {filepath}{Style.RESET_ALL}")
            sys.exit(1)

    def validate_url(self, url):
        """Validates if the URL is properly formatted with scheme and domain."""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False

    def get_current_value(self, filepath, key_path):
        """Gets current value from JSON file following a key path"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                current = data
                for key in key_path:
                    current = current[key]
                return current
        except:
            return None

    def update_certificate_template(self, data):
        # Get user input for name and email
        current_name = self.get_current_value(
            "root-cert-template.json", ["certificate", "subject", "displayName"])
        current_email = self.get_current_value(
            "root-cert-template.json", ["certificate", "subject", "contact", "email"])

        print("\nCertificate Holder Information:")
        self.display_name = input(
            f"{Fore.CYAN}Enter your name{' (press Enter for ' + current_name + ')' if current_name else ''}: {Style.RESET_ALL}").strip()
        if not self.display_name and current_name:
            self.display_name = current_name

        while True:
            self.email = input(
                f"{Fore.CYAN}Enter your email{' (press Enter for ' + current_email + ')' if current_email else ''}: {Style.RESET_ALL}").strip()
            if not self.email and current_email:
                self.email = current_email
                break
            if '@' in self.email and '.' in self.email:  # Basic email validation
                break
            print(
                f"{Fore.RED}Invalid email format. Please enter a valid email address.{Style.RESET_ALL}")

        # Read the public key data from root.pub.json
        try:
            with open("root.pub.json", 'r') as f:
                self.public_key_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(
                f"{Fore.RED}  - Error reading root.pub.json: {str(e)}{Style.RESET_ALL}")
            sys.exit(1)

        # Create new data structure with schema first
        new_data = {
            "$schema": "https://schemas.golem.network/v1/certificate.schema.json",
            "certificate": data["certificate"]
        }

        # Update subject information
        new_data["certificate"]["subject"] = {
            "displayName": self.display_name,
            "contact": {
                "email": self.email
            }
        }

        # Add public key data and update other fields
        new_data["certificate"]["publicKey"] = self.public_key_data

        # Update validity dates
        now = datetime.now(tz.UTC)
        next_year = now + timedelta(days=365)
        self.validity_period = {
            "notBefore": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notAfter": next_year.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        new_data["certificate"]["validityPeriod"] = self.validity_period

        print(f"{Fore.GREEN}  - Updated certificate information:{Style.RESET_ALL}")
        print(f"    - Name: {self.display_name}")
        print(f"    - Email: {self.email}")
        print(
            f"    - Validity: {self.validity_period['notBefore']} to {self.validity_period['notAfter']}")
        print(
            f"{Fore.GREEN}  - Added public key data from root.pub.json{Style.RESET_ALL}")

        return new_data

    def update_node_descriptor(self, data):
        # Get the validity period from the signed certificate
        try:
            with open("root-cert-template.signed.json", 'r') as f:
                cert_data = json.load(f)
                cert_validity = cert_data["certificate"]["validityPeriod"]

                # Convert the times to datetime objects
                cert_not_before = datetime.strptime(
                    cert_validity["notBefore"], "%Y-%m-%dT%H:%M:%SZ")
                cert_not_after = datetime.strptime(
                    cert_validity["notAfter"], "%Y-%m-%dT%H:%M:%SZ")

                # Adjust node validity to be within cert's validity period
                node_not_before = cert_not_before + \
                    timedelta(
                        seconds=1)  # Start 1 second after cert's notBefore
                node_not_after = cert_not_after - \
                    timedelta(seconds=1)  # End 1 second before cert's notAfter

                self.validity_period = {
                    "notBefore": node_not_before.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "notAfter": node_not_after.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(
                f"{Fore.RED}  - Error reading validity period from signed certificate: {str(e)}{Style.RESET_ALL}")
            sys.exit(1)

        data["$schema"] = "https://schemas.golem.network/v1/node-descriptor.schema.json"
        data["nodeDescriptor"]["nodeId"] = self.node_id
        data["nodeDescriptor"]["validityPeriod"] = self.validity_period

        if self.outbound_mode == "whitelist":
            data["nodeDescriptor"]["permissions"]["outbound"] = {
                "urls": self.urls}
            print(
                f"{Fore.GREEN}  - Node descriptor updated with specific URLs{Style.RESET_ALL}")
        else:
            data["nodeDescriptor"]["permissions"]["outbound"] = "unrestricted"
            print(
                f"{Fore.GREEN}  - Node descriptor updated with unrestricted outbound access{Style.RESET_ALL}")

        # Display the updated validity period
        print(
            f"{Fore.GREEN}  - Node descriptor validity period set from {self.validity_period['notBefore']} to {self.validity_period['notAfter']}{Style.RESET_ALL}")
        return data

    def main(self):
        # --- Step 1: Generate Root Key Pair ---
        print(
            f"{Fore.CYAN}Step 1: Generating root key pair...{Style.RESET_ALL}")
        self.run_command(["create-key-pair", "root"])

        # --- Step 2: Add $schema and Update Dates in root-cert-template.json ---
        print(
            f"{Fore.CYAN}Step 2: Adding schema and updating dates in root-cert-template.json...{Style.RESET_ALL}")
        self.update_json_file(
            "root-cert-template.json", self.update_certificate_template)

        # --- Step 3: Configure Outbound Permissions ---
        print(f"\n{Fore.YELLOW}Outbound Access Configuration{Style.RESET_ALL}")
        print("You can either:")
        print(
            "1. Allow unrestricted access to all URLs (easiest to use but requires more trust from providers)")
        print(
            "2. Specify a whitelist of allowed URLs (more restrictive, easier to gain provider trust by showing specific URLs)")

        current_outbound = self.get_current_value(
            "root-cert-template.json", ["certificate", "permissions", "outbound"])
        current_mode = "y" if current_outbound == "unrestricted" else "n" if isinstance(
            current_outbound, dict) else None

        whitelist_choice = input(
            f"\nDo you want to restrict outbound access to specific URLs? (y=unrestricted, n=whitelist){' (press Enter for ' + current_mode + ')' if current_mode else ''}: ").lower()
        if not whitelist_choice and current_mode:
            whitelist_choice = current_mode

        if whitelist_choice == "n":
            self.outbound_mode = "whitelist"
            current_urls = self.get_current_value("root-cert-template.json", [
                                                  "certificate", "permissions", "outbound", "urls"]) or []
            self.urls = []

            print(
                "\nEnter URLs to whitelist (must include https:// or http://)")
            print("You must enter at least one URL")

            if current_urls:
                print(f"\nCurrent URLs:")
                for url in current_urls:
                    print(f"  - {url}")
                use_current = input("\nUse current URLs? (y/n): ").lower()
                if use_current == 'y':
                    self.urls = current_urls

            while not self.urls:  # Keep asking until at least one valid URL is entered
                url = input(f"{Fore.CYAN}Enter URL: {Style.RESET_ALL}").strip()
                if self.validate_url(url):
                    self.urls.append(url)
                else:
                    print(
                        f"{Fore.RED}Invalid URL format. Please use format like 'https://example.com'{Style.RESET_ALL}")

            # Allow adding additional URLs
            print("\nEnter additional URLs (or press Enter when done)")
            while True:
                url = input(f"{Fore.CYAN}Enter URL: {Style.RESET_ALL}").strip()
                if not url:
                    break
                if self.validate_url(url):
                    self.urls.append(url)
                else:
                    print(
                        f"{Fore.RED}Invalid URL format. Please use format like 'https://example.com'{Style.RESET_ALL}")

            def update_outbound_urls(data):
                data["certificate"]["permissions"]["outbound"] = {
                    "urls": self.urls}
                print(
                    f"{Fore.GREEN}  - Outbound access restricted to:{Style.RESET_ALL}")
                for url in self.urls:
                    print(f"    - {url}")
                return data

            self.update_json_file(
                "root-cert-template.json", update_outbound_urls)

        else:
            self.outbound_mode = "unrestricted"

            def update_outbound_unrestricted(data):
                data["certificate"]["permissions"]["outbound"] = "unrestricted"
                print(
                    f"{Fore.GREEN}  - Outbound access: Unrestricted (all URLs allowed){Style.RESET_ALL}")
                return data

            self.update_json_file(
                "root-cert-template.json", update_outbound_unrestricted)

        # --- Step 4: Self-Sign Certificate ---
        print(
            f"\n{Fore.CYAN}Step 3: Signing the certificate...{Style.RESET_ALL}")
        self.run_command(
            ["self-sign-certificate", "root-cert-template.json", "root.key.json"])
        print(
            f"{Fore.GREEN}  - Certificate signed successfully! Created root-cert-template.signed.json{Style.RESET_ALL}")

        # --- Step 5: Update Node Descriptor ---
        print(
            f"\n{Fore.CYAN}Step 4: Updating node descriptor...{Style.RESET_ALL}")
        current_node_id = self.get_current_value(
            "node-descriptor.json", ["nodeDescriptor", "nodeId"])

        print(f"\nTo get your Node ID, run this command:")
        print(f"{Fore.GREEN}yagna id show{Style.RESET_ALL}")
        print(
            f"The Node ID will look like: {Fore.YELLOW}0xc0ffee254729296a45a3885639AC7E10F9d54979{Style.RESET_ALL}")

        while True:
            self.node_id = input(
                f"\nEnter your Node ID{' (press Enter for ' + current_node_id + ')' if current_node_id else ''}: ").lower()
            if not self.node_id and current_node_id:
                self.node_id = current_node_id
                break
            if self.is_valid_eth_address(self.node_id):
                break
            print(
                f"{Fore.RED}Invalid Node ID format. Must be a 42-character Ethereum address starting with '0x'{Style.RESET_ALL}")

        self.update_json_file(
            "node-descriptor.json", self.update_node_descriptor)

        # --- Step 6: Sign Node Descriptor ---
        print(
            f"\n{Fore.CYAN}Step 5: Signing the node descriptor...{Style.RESET_ALL}")
        self.run_command(["sign", "node-descriptor.json",
                         "root-cert-template.signed.json", "root.key.json"])
        print(
            f"{Fore.GREEN}  - Node descriptor signed successfully! Created node-descriptor.signed.json{Style.RESET_ALL}")

        # --- Step 7: Final Instructions and User Guidance ---
        print(f"\n{Fore.GREEN}{'='*70}")
        print(f"🎉  Setup Complete!  🎉")
        print(f"{'='*70}{Style.RESET_ALL}\n")

        print("Congratulations! You just created your self-signed certificate for outbound internet access in tasks.")
        print(
            "For your tasks to work, providers need to trust your certificate before your outbound requests will work inside tasks.\n")

        print(f"{Fore.CYAN}Next Steps:{Style.RESET_ALL}")
        print(
            "1. Make your certificate available for download (e.g. via GitHub Gist)")
        print(
            "2. Post a message in the Golem Discord #providers channel (chat.golem.network):")
        print(f"{Fore.YELLOW}Example message:{Style.RESET_ALL}")
        print('    "Hi providers! I have a task that requires outbound internet access.')
        print('    To run it, you\'ll need to trust my certificate first:')
        print('    1. Download the certificate from: [YOUR_DOWNLOAD_LINK]')
        print('    2. Run this command:')
        print(
            f'    {Fore.GREEN}ya-provider rule set outbound partner import-cert root-cert-template.signed.json --mode all{Style.RESET_ALL}"\n')

        print(f"{Fore.CYAN}Using the Node Descriptor in Tasks:{Style.RESET_ALL}")
        print(
            "When requesting tasks, you must include the node descriptor:")
        print(
            "- For Python yapapi: Include 'node-descriptor.json' in your Task model")
        print(
            "- For JS/TS yajsapi: Pass the descriptor in your Task definition")
        print(
            "- For CLI commands: Use --node-descriptor node-descriptor.json\n")

        print(f"{Fore.YELLOW}Documentation:{Style.RESET_ALL}")
        print(
            "For detailed examples of using node descriptors with different task types, visit:")
        print(
            "https://docs.golem.network/docs/creators/javascript/guides/using-vm-runtime")
        print(
            "https://docs.golem.network/docs/creators/python/guides/using-vm-runtime\n")

        print(
            f"{Fore.CYAN}Thank you for contributing to the Golem Network!{Style.RESET_ALL}\n")


# Add the module-level main function
def main():
    cert_manager = CertificateManager()
    cert_manager.main()
