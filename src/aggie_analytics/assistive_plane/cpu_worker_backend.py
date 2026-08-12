from __future__ import annotations

from dataclasses import dataclass

from .orchestration import validate_cpu_worker_identity


@dataclass(frozen=True)
class CpuWorkerIdentity:
    dns_name: str
    os_name: str
    online: bool
    allowed_dns_name: str = "comfy-v4-cpu-01.tail9b05ab.ts.net"

    def validate(self) -> None:
        validate_cpu_worker_identity(
            dns_name=self.dns_name,
            os_name=self.os_name,
            online=self.online,
            allowed_dns_name=self.allowed_dns_name,
        )
