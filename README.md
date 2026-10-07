# ARTXploit
Exploit Development &amp; Research for Autumn-27/ARTEX

## Executive Summary

## Exploit Reproduction Environment
| Field             | Value                                                     |
|:------------------|:----------------------------------------------------------|
| Hypervisor        | KVM QEMU emulator version 10.2.2 (qemu-10.2.2-1.fc44)     |
| Guest VM          | Ubuntu 26.04.1 Live Server AMD64                          |
|                   |                                                           |
| Product           | ARTEX AI                                                  |
| Version           | `v0.3.14`                                                 |
| Commit            | `b55ceb1fdd84a813d77de09a06af83d323a81f85`                |
|                   |                                                           |
| Go                | go version go1.26.3 linux/amd64                           |
| PostgreSQL        | psql (PostgreSQL) 18.6                                    |
| npm               | 9.2.0                                                     |

### Configuration
```json
{
    "database": {
        "host": "127.0.0.1",
        "port": 5432,
        "user": "artex",
        "password": "artxploit",
        "dbname": "artex",
        "sslmode": "disable"
    }
}
```

### API Key
| Provider  | Expires       | API Key                                                   |
|:----------|:--------------|:----------------------------------------------------------|
| Groq      | 10/14/2026    | `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`|


### Post Installation

| Setup Page | Dashboard |
|-|-|
| ![Setup](./screenshots/Screenshot%20From%202026-10-07%2018-07-27.png) | ![Dashboard](./screenshots/Screenshot%20From%202026-10-07%2018-10-28.png) |

![Console](./screenshots/Screenshot%20From%202026-10-07%2018-11-18.png)

* Commit: [b55ceb1fdd84a813d77de09a06af83d323a81f85](https://github.com/Autumn-27/ARTEX/tree/b55ceb1fdd84a813d77de09a06af83d323a81f85)
* Release: [v0.3.14](https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14)

## Exploit Usage
```bash
python3 artxploit.py -t [TARGET] -p [NEW_PASSWORD]
```

## References
* [https://artex-demo.vercel.app/](https://artex-demo.vercel.app/)
* [https://github.com/Autumn-27/ARTEX](https://github.com/Autumn-27/ARTEX)
* [https://github.com/Autumn-27/Norma](https://github.com/Autumn-27/Norma)
* [https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14](https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14)