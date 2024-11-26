DEFAULT_NODE_DESCRIPTOR = {
    "nodeDescriptor": {
        "nodeId": "",
        "permissions": {
            "outbound": "unrestricted"
        },
        "validityPeriod": {
            "notBefore": "",
            "notAfter": ""
        }
    },
    "$schema": "https://schemas.golem.network/v1/node-descriptor.schema.json"
}

DEFAULT_ROOT_CERT_TEMPLATE = {
    "$schema": "https://schemas.golem.network/v1/certificate.schema.json",
    "certificate": {
        "keyUsage": [
            "signCertificate",
            "signNode"
        ],
        "permissions": {
            "outbound": "unrestricted"
        },
        "subject": {
            "displayName": "",
            "contact": {
                "email": ""
            }
        },
        "validityPeriod": {
            "notBefore": "",
            "notAfter": ""
        },
        "publicKey": {
            "algorithm": "EdDSA",
            "key": "",
            "parameters": {
                "scheme": "Ed25519"
            }
        }
    }
}
DEFAULT_WHITELIST_MANIFEST = {
    "version": "0.1.0",
    "createdAt": "",
    "expiresAt": "",
    "metadata": {
        "name": "",
        "description": "",
        "version": "0.1.0"
    },
    "payload": [
        {
            "platform": {
                "arch": "x86_64",
                "os": "linux"
            },
            "urls": [],
            "hash": ""
        }
    ],
    "compManifest": {
        "version": "0.1.0",
        "net": {
            "inet": {
                "out": {
                    "protocols": ["https"],
                    "urls": []
                }
            }
        }
    }
}

DEFAULT_UNRESTRICTED_MANIFEST = {
    "version": "0.1.0",
    "createdAt": "",
    "expiresAt": "",
    "metadata": {
        "name": "",
        "description": "",
        "version": "0.1.0"
    },
    "payload": [
        {
            "platform": {
                "arch": "x86_64",
                "os": "linux"
            },
            "urls": [],
            "hash": ""
        }
    ],
    "compManifest": {
        "version": "0.1.0",
        "net": {
            "inet": {
                "out": {
                    "protocols": ["https"],
                    "unrestricted": {
                        "urls": True
                    }
                }
            }
        }
    }
}
