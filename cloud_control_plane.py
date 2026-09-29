from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeploymentResult:
    provider: str
    success: bool
    message: str
    output: str = ""


class CloudProvider:
    name = "base"

    def configured(self) -> bool:
        return False

    def deploy(self) -> DeploymentResult:
        raise NotImplementedError

    def health(self) -> DeploymentResult:
        raise NotImplementedError

    def recover(self) -> DeploymentResult:
        raise NotImplementedError


class OracleProvider(CloudProvider):
    name = "oracle"

    def __init__(self) -> None:
        self.host = os.getenv("GAIRUS_ORACLE_HOST", "").strip()
        self.user = os.getenv("GAIRUS_ORACLE_USER", "").strip()
        self.key_path = os.getenv(
            "GAIRUS_ORACLE_SSH_KEY_PATH",
            "/etc/gairus/oracle_key",
        ).strip()
        self.app_dir = os.getenv(
            "GAIRUS_ORACLE_APP_DIR",
            "/opt/gairus",
        ).strip()
        self.repo = os.getenv(
            "GAIRUS_GITHUB_REPO",
            "https://github.com/zyrvion/Gairus-.git",
        ).strip()
        self.branch = os.getenv("GAIRUS_GITHUB_BRANCH", "main").strip()

    def configured(self) -> bool:
        return bool(
            self.host
            and self.user
            and self.key_path
            and os.path.exists(os.path.expanduser(self.key_path))
        )

    def _ssh(self, command: str) -> subprocess.CompletedProcess[str]:
        target = f"{self.user}@{self.host}"

        args = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-i",
            os.path.expanduser(self.key_path),
            target,
            command,
        ]

        return subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )

    def deploy(self) -> DeploymentResult:
        if not self.configured():
            return DeploymentResult(
                self.name,
                False,
                "Oracle non configuré",
            )

        qdir = shlex.quote(self.app_dir)
        qrepo = shlex.quote(self.repo)
        qbranch = shlex.quote(self.branch)

        command = f"""
set -eu
mkdir -p {qdir}
if [ ! -d {qdir}/.git ]; then
    git clone --branch {qbranch} {qrepo} {qdir}
else
    cd {qdir}
    git fetch origin {qbranch}
    git reset --hard origin/{qbranch}
fi
cd {qdir}
docker compose up -d --build
docker compose ps
""".strip()

        result = self._ssh(command)

        return DeploymentResult(
            self.name,
            result.returncode == 0,
            "Déploiement Oracle terminé"
            if result.returncode == 0
            else "Échec du déploiement Oracle",
            result.stdout + result.stderr,
        )

    def health(self) -> DeploymentResult:
        if not self.configured():
            return DeploymentResult(
                self.name,
                False,
                "Oracle non configuré",
            )

        qdir = shlex.quote(self.app_dir)

        command = f"""
set -eu
cd {qdir}
curl -fsS --max-time 10 http://127.0.0.1:10000/health
docker compose ps
""".strip()

        result = self._ssh(command)

        return DeploymentResult(
            self.name,
            result.returncode == 0,
            "Gaïrus est opérationnel sur Oracle"
            if result.returncode == 0
            else "Healthcheck Oracle échoué",
            result.stdout + result.stderr,
        )

    def recover(self) -> DeploymentResult:
        if not self.configured():
            return DeploymentResult(
                self.name,
                False,
                "Oracle non configuré",
            )

        qdir = shlex.quote(self.app_dir)

        command = f"""
set -eu
cd {qdir}
docker compose restart
sleep 5
curl -fsS --max-time 10 http://127.0.0.1:10000/health
""".strip()

        result = self._ssh(command)

        return DeploymentResult(
            self.name,
            result.returncode == 0,
            "Récupération Oracle terminée"
            if result.returncode == 0
            else "Récupération Oracle échouée",
            result.stdout + result.stderr,
        )


class CloudControlPlane:
    def __init__(self) -> None:
        self.providers = [
            OracleProvider(),
        ]

    def available(self) -> list[str]:
        return [
            provider.name
            for provider in self.providers
            if provider.configured()
        ]

    def provider(self, name: Optional[str] = None) -> Optional[CloudProvider]:
        if name:
            for provider in self.providers:
                if provider.name == name and provider.configured():
                    return provider
            return None

        for provider in self.providers:
            if provider.configured():
                return provider

        return None

    def deploy(self, provider_name: Optional[str] = None) -> DeploymentResult:
        provider = self.provider(provider_name)

        if provider is None:
            return DeploymentResult(
                "none",
                False,
                "Aucun fournisseur cloud configuré",
            )

        return provider.deploy()

    def health(self, provider_name: Optional[str] = None) -> DeploymentResult:
        provider = self.provider(provider_name)

        if provider is None:
            return DeploymentResult(
                "none",
                False,
                "Aucun fournisseur cloud configuré",
            )

        return provider.health()

    def recover(self, provider_name: Optional[str] = None) -> DeploymentResult:
        provider = self.provider(provider_name)

        if provider is None:
            return DeploymentResult(
                "none",
                False,
                "Aucun fournisseur cloud configuré",
            )

        return provider.recover()


def get_cloud_control_plane() -> CloudControlPlane:
    return CloudControlPlane()


def cloud_deploy(provider: Optional[str] = None) -> dict:
    result = get_cloud_control_plane().deploy(provider)
    return {
        "provider": result.provider,
        "success": result.success,
        "message": result.message,
        "output": result.output,
    }


def cloud_health(provider: Optional[str] = None) -> dict:
    result = get_cloud_control_plane().health(provider)
    return {
        "provider": result.provider,
        "success": result.success,
        "message": result.message,
        "output": result.output,
    }


def cloud_recover(provider: Optional[str] = None) -> dict:
    result = get_cloud_control_plane().recover(provider)
    return {
        "provider": result.provider,
        "success": result.success,
        "message": result.message,
        "output": result.output,
    }


if __name__ == "__main__":
    action = os.getenv("GAIRUS_CLOUD_ACTION", "health").strip().lower()

    if action == "deploy":
        result = cloud_deploy()
    elif action == "recover":
        result = cloud_recover()
    else:
        result = cloud_health()

    print(json.dumps(result, ensure_ascii=False, indent=2))
