from .binary_manager import BinaryManager
from colorama import init, Fore, Style
from dateutil import tz
from datetime import datetime, timedelta
import os
import json
import subprocess
from urllib.parse import urlparse
import sys
from .templates import DEFAULT_NODE_DESCRIPTOR, DEFAULT_ROOT_CERT_TEMPLATE, DEFAULT_WHITELIST_MANIFEST, DEFAULT_UNRESTRICTED_MANIFEST
import re

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
        self.image_url = None
        self.image_hash = None

    def is_valid_sha3(self, hash_str):
        """Validates if the string is a valid SHA3 hash (56 hex characters)"""
        return bool(re.match(r'^[a-fA-F0-9]{56}$', hash_str))

    def create_manifest(self):
        print(f"\n{Fore.YELLOW}=== Manifest Creation ==={Style.RESET_ALL}")

        # Get image information
        print(f"\nYou can either provide a URL to download the image or its SHA3 hash.")
        while True:
            image_type = input(f"{Fore.CYAN}Enter 'url' or 'hash' [url]: {Style.RESET_ALL}").lower()
            if not image_type:
                image_type = 'url'
            if image_type in ['url', 'hash']:
                break
            print(f"{Fore.RED}Please enter 'url' or 'hash'{Style.RESET_ALL}")

        if image_type == 'url':
            while True:
                self.image_url = input(f"{Fore.CYAN}Enter image URL (e.g., https://example.com/image.gvmi): {Style.RESET_ALL}").strip()
                if self.validate_url(self.image_url):
                    break
                print(f"{Fore.RED}Invalid URL format{Style.RESET_ALL}")
        else:
            while True:
                hash_input = input(f"{Fore.CYAN}Enter SHA3 hash (without 'sha3:' prefix), e.g., '505509fce98bfb9067125334e58a3340615f863acf258d7275ca1265': {Style.RESET_ALL}").strip()
                if self.is_valid_sha3(hash_input):
                    self.image_hash = f"sha3:{hash_input}"
                    break
                print(f"{Fore.RED}Invalid SHA3 hash format. Should be 56 hex characters{Style.RESET_ALL}")

        # Get manifest metadata
        manifest_name = input(f"{Fore.CYAN}Enter manifest name: {Style.RESET_ALL}").strip()
        manifest_desc = input(f"{Fore.CYAN}Enter manifest description: {Style.RESET_ALL}").strip()

        # Create manifest based on outbound mode
        manifest = (DEFAULT_WHITELIST_MANIFEST if self.outbound_mode == "whitelist"
                    else DEFAULT_UNRESTRICTED_MANIFEST).copy()

        # Update manifest content
        now = datetime.now(tz.UTC)
        manifest["createdAt"] = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        manifest["expiresAt"] = (now + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        manifest["metadata"].update({
            "name": manifest_name,
            "description": manifest_desc
        })

        if self.image_url:
            manifest["payload"][0]["urls"] = [self.image_url]
        if self.image_hash:
            manifest["payload"][0]["hash"] = self.image_hash

        if self.outbound_mode == "whitelist":
            manifest["compManifest"]["net"]["inet"]["out"]["urls"] = self.urls

        # Save manifest
        filename = "manifest-whitelist.json" if self.outbound_mode == "whitelist" else "manifest-unrestricted.json"
        with open(filename, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"\n{Fore.GREEN}Created manifest: {filename}{Style.RESET_ALL}")

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
                f"{Fore.RED}Error: Command failed with error code {e.returncode}:\n{e.stderr}{Style.RESET_ALL}")
            sys.exit(1)
        except FileNotFoundError:
            print(
                f"{Fore.RED}Error: Command not found: {command[0]}. Is it installed and in your PATH?{Style.RESET_ALL}")
            sys.exit(1)

    def update_json_file(self, filepath, update_function, overwrite_existing=True):
        """Reads a JSON file, applies an update function, and writes it back."""
        try:
            # If file doesn't exist, use default template
            if not os.path.exists(filepath):
                data = DEFAULT_NODE_DESCRIPTOR if filepath == "node-descriptor.json" else DEFAULT_ROOT_CERT_TEMPLATE
            else:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                if not overwrite_existing:
                    # Do not overwrite existing file
                    return

            updated_data = update_function(data)
            with open(filepath, 'w') as f:
                json.dump(updated_data, f, indent=2)
        except json.JSONDecodeError:
            print(
                f"{Fore.RED}Error: Invalid JSON format in file: {filepath}{Style.RESET_ALL}")
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
        print(f"\n{Fore.YELLOW}=== Certificate Holder Information ==={Style.RESET_ALL}")
        self.display_name = input(
            f"{Fore.CYAN}Enter your name: {Style.RESET_ALL}").strip()

        while True:
            self.email = input(
                f"{Fore.CYAN}Enter your email: {Style.RESET_ALL}").strip()
            if '@' in self.email and '.' in self.email:  # Basic email validation
                break
            print(f"{Fore.RED}Invalid email format. Please enter a valid email address.{Style.RESET_ALL}")

        # Read the public key data from root.pub.json
        try:
            with open("root.pub.json", 'r') as f:
                self.public_key_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(
                f"{Fore.RED}Error reading root.pub.json: {str(e)}{Style.RESET_ALL}")
            sys.exit(1)

        # Create new data structure with schema first
        new_data = {
            "$schema": "https://schemas.golem.network/v1/certificate.schema.json",
            "certificate": data.get("certificate", {})
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
                f"{Fore.RED}Error reading validity period from signed certificate: {str(e)}{Style.RESET_ALL}")
            sys.exit(1)

        data["$schema"] = "https://schemas.golem.network/v1/node-descriptor.schema.json"
        data["nodeDescriptor"]["nodeId"] = self.node_id
        data["nodeDescriptor"]["validityPeriod"] = self.validity_period

        if self.outbound_mode == "whitelist":
            data["nodeDescriptor"]["permissions"]["outbound"] = {
                "urls": self.urls}
        else:
            data["nodeDescriptor"]["permissions"]["outbound"] = "unrestricted"

        return data

    def main(self):
        # Generate Root Key Pair if it doesn't exist
        if not (os.path.exists("root.key.json") and os.path.exists("root.pub.json")):
            self.run_command(["create-key-pair", "root"])
        else:
            print(f"\n{Fore.GREEN}Root key pair already exists, skipping key pair creation.{Style.RESET_ALL}")

        # Update or use existing root-cert-template.json
        if not os.path.exists("root-cert-template.json"):
            # Add $schema and Update Dates in root-cert-template.json
            self.update_json_file(
                "root-cert-template.json", self.update_certificate_template)

            # Configure Outbound Permissions
            print(f"\n{Fore.YELLOW}=== Outbound Access Configuration ==={Style.RESET_ALL}")
            print("You can either:")
            print(
                f"{Fore.GREEN}1. Request unrestricted access to all URLs{Style.RESET_ALL} (requires more trust from providers)")
            print(
                f"{Fore.GREEN}2. Specify a whitelist of allowed URLs{Style.RESET_ALL} (more restrictive, easier to gain provider trust)")

            whitelist_choice = input(
                f"\n{Fore.CYAN}Do you want to request unrestricted outbound access to all URLs? (y/n): {Style.RESET_ALL}").lower()

            if whitelist_choice == "y":
                self.outbound_mode = "unrestricted"

                def update_outbound_unrestricted(data):
                    data["certificate"]["permissions"]["outbound"] = "unrestricted"
                    return data

                self.update_json_file(
                    "root-cert-template.json", update_outbound_unrestricted, overwrite_existing=True)
            else:
                self.outbound_mode = "whitelist"
                self.urls = []

                print(
                    f"\n{Fore.YELLOW}Enter URLs to whitelist (must include https:// or http://){Style.RESET_ALL}")
                print("You must enter at least one URL")

                while not self.urls:  # Keep asking until at least one valid URL is entered
                    url = input(f"{Fore.CYAN}Enter URL (e.g., https://example.com/api): {Style.RESET_ALL}").strip()
                    if self.validate_url(url):
                        self.urls.append(url)
                    else:
                        print(
                            f"{Fore.RED}Invalid URL format. Please use format like 'https://example.com'{Style.RESET_ALL}")

                # Allow adding additional URLs
                print(f"{Fore.YELLOW}Enter additional URLs (or press Enter when done){Style.RESET_ALL}")
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
                    return data

                self.update_json_file(
                    "root-cert-template.json", update_outbound_urls, overwrite_existing=True)
        else:
            print(f"\n{Fore.GREEN}root-cert-template.json already exists, using existing template.{Style.RESET_ALL}")
            # Determine outbound mode from existing root-cert-template.json
            current_outbound = self.get_current_value(
                "root-cert-template.json", ["certificate", "permissions", "outbound"])
            if current_outbound == "unrestricted":
                self.outbound_mode = "unrestricted"
            elif isinstance(current_outbound, dict):
                self.outbound_mode = "whitelist"
                self.urls = current_outbound.get("urls", [])
            else:
                print(
                    f"{Fore.RED}Error determining outbound mode from existing root-cert-template.json.{Style.RESET_ALL}")
                sys.exit(1)

            # Read the public key data from root.pub.json
            try:
                with open("root.pub.json", 'r') as f:
                    self.public_key_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(
                    f"{Fore.RED}Error reading root.pub.json: {str(e)}{Style.RESET_ALL}")
                sys.exit(1)

        # Self-Sign Certificate if it doesn't exist
        if not os.path.exists("root-cert-template.signed.json"):
            self.run_command(
                ["self-sign-certificate", "root-cert-template.json", "root.key.json"])
        else:
            print(f"\n{Fore.GREEN}root-cert-template.signed.json already exists, skipping self-signing certificate.{Style.RESET_ALL}")

        # Update Node Descriptor
        print(f"\n{Fore.YELLOW}=== Node Descriptor Configuration ==={Style.RESET_ALL}")
        current_node_id = self.get_current_value(
            "node-descriptor.json", ["nodeDescriptor", "nodeId"])

        print(f"\nTo get your Node ID, run this command:")
        print(f"{Fore.GREEN}yagna id show{Style.RESET_ALL}")
        print(
            f"The Node ID will look like: {Fore.YELLOW}0xc0ffee254729296a45a3885639AC7E10F9d54979{Style.RESET_ALL}")

        while True:
            self.node_id = input(
                f"{Fore.CYAN}Enter your Node ID{' (press Enter for ' + current_node_id + ')' if current_node_id else ''}: {Style.RESET_ALL}").lower()
            if not self.node_id and current_node_id:
                self.node_id = current_node_id
                break
            if self.is_valid_eth_address(self.node_id):
                break
            print(
                f"{Fore.RED}Invalid Node ID format. Must be a 42-character Ethereum address starting with '0x'{Style.RESET_ALL}")

        # Update node-descriptor.json
        self.update_json_file(
            "node-descriptor.json", self.update_node_descriptor)

        # Sign Node Descriptor
        self.run_command(["sign", "node-descriptor.json",
                          "root-cert-template.signed.json", "root.key.json"])

        # Create Manifest
        self.create_manifest()

        # Final Instructions and User Guidance
        print(f"\n{Fore.GREEN}{'='*70}")
        print(f"🎉  Setup Complete!  🎉")
        print(f"{'='*70}{Style.RESET_ALL}\n")

        print(f"Congratulations! You have successfully created your self-signed certificate for outbound internet access in tasks.")
        print(f"To enable outbound requests for your tasks, providers need to trust your certificate.\n")

        print(f"{Fore.YELLOW}Next Steps:{Style.RESET_ALL}")
        print(f"1. Make your signed certificate available for providers (e.g., upload it to GitHub Gist).")
        print(f"2. Share your certificate and request trust from providers in the Golem Discord `#providers` channel:")
        print(f"   {Fore.CYAN}https://chat.golem.network{Style.RESET_ALL}")
        print(f"   Provide the download link and include instructions to import it using:")
        print(f"   {Fore.GREEN}ya-provider rule set outbound partner import-cert root-cert-template.signed.json --mode all{Style.RESET_ALL}\n")

        print(f"3. Attach the generated `manifest.json` and `node-descriptor.signed.json` to your tasks.")
        print(f"For detailed integration guides, refer to the following resources:\n")
        print(f"   - {Fore.CYAN}dapp-runner: https://docs.golem.network/docs/creators/dapps/internet-access-in-dapps{Style.RESET_ALL}\n")
        print(f"   - {Fore.CYAN}yapapi: https://docs.golem.network/docs/creators/python/tutorials/service-example-6-external-api-request{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}Thank you for contributing to the Golem Network!{Style.RESET_ALL}\n")


# Add the module-level main function
def main():
    cert_manager = CertificateManager()
    cert_manager.main()