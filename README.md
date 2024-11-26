# Golem Certificate Companion

A user-friendly command-line tool that simplifies outbound networking setup on the Golem Network. Instead of manually managing certificates, keys, and descriptors, this tool guides you through a simple interactive process to generate all required files.

## Overview

Setting up outbound networking on Golem traditionally requires multiple manual steps including key generation, certificate creation, and descriptor signing. The Golem Certificate Companion automates this entire process, handling all the cryptographic operations behind the scenes.

With a single command and a few simple prompts, you can:
- Generate all required cryptographic keys
- Create and sign your certificates
- Configure outbound access (unrestricted or URL whitelist)
- Generate a properly signed node descriptor

## Installation

```bash
pip install golem-cert-companion
```

## Quick Start

1. Run the tool:
```bash
golem-cert-companion
```

2. Answer a few simple questions:
   - Your name and email
   - Whether you want unrestricted access or specific URLs
   - Your Golem node ID (run `yagna id show` to get this)

That's it! The tool handles all the complex certificate generation and signing automatically.

## Provider Setup

After generating your certificate:

1. Share your signed certificate (`root-cert-template.signed.json`) with providers
2. Providers can enable your outbound access by running:
```bash
ya-provider rule set outbound partner import-cert root-cert-template.signed.json --mode all
```
## Using in Your Tasks

We've covered in our documentation how to use the files in your tasks:

### Yapapi
https://...

### golem-js
https://...

### Dapp-runner (golem-compose)
https://...


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

