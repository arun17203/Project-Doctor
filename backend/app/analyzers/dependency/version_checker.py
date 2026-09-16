import re
import requests
from typing import Optional, Dict, Tuple
from packaging import version as pkg_version

REQUEST_TIMEOUT_SECONDS = 2.5


class VersionChecker:
    def __init__(self):
        # Cache: (name.lower(), ecosystem.lower()) -> Optional[str]
        self._cache: Dict[Tuple[str, str], Optional[str]] = {}
        # Mock map for testing
        self._mock_data: Dict[Tuple[str, str], str] = {}

    def set_mock_latest(self, package_name: str, ecosystem: str, latest_version: str):
        """Set mock latest version for testing without external network calls."""
        key = (package_name.lower(), ecosystem.lower())
        self._mock_data[key] = latest_version

    def get_latest_version(self, package_name: str, ecosystem: str) -> Optional[str]:
        """Fetch the latest stable version from the official ecosystem package registry."""
        clean_name = package_name.strip()
        key = (clean_name.lower(), ecosystem.lower())

        if key in self._mock_data:
            return self._mock_data[key]

        if key in self._cache:
            return self._cache[key]

        latest: Optional[str] = None

        try:
            if ecosystem.lower() in {"python", "pypi"}:
                url = f"https://pypi.org/pypi/{clean_name}/json"
                res = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "Project-Doctor/1.0"})
                if res.status_code == 200:
                    latest = res.json().get("info", {}).get("version")

            elif ecosystem.lower() in {"node", "nodejs", "javascript", "npm"}:
                url = f"https://registry.npmjs.org/{clean_name}/latest"
                res = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "Project-Doctor/1.0"})
                if res.status_code == 200:
                    latest = res.json().get("version")

            elif ecosystem.lower() in {"java", "maven"}:
                if ":" in clean_name:
                    group_id, artifact_id = clean_name.split(":", 1)
                    url = f"https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}&rows=1&wt=json"
                    res = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "Project-Doctor/1.0"})
                    if res.status_code == 200:
                        docs = res.json().get("response", {}).get("docs", [])
                        if docs:
                            latest = docs[0].get("latestVersion")
        except Exception:
            latest = None

        self._cache[key] = latest
        return latest

    def determine_status(
        self,
        current_version: Optional[str],
        latest_version: Optional[str],
        vulnerability_count: int,
        was_network_error: bool = False,
    ) -> str:
        """Determine dependency status: VULNERABLE, OUTDATED, CURRENT, or UNKNOWN.
        Precedence:
        1. VULNERABLE if confirmed vulnerabilities > 0
        2. OUTDATED if latest_version is higher than current_version
        3. CURRENT if current_version >= latest_version
        4. UNKNOWN if version or latest cannot be reliably compared
        """
        # 1. Vulnerability has highest precedence
        if vulnerability_count > 0:
            return "VULNERABLE"

        # If network error occurred during vulnerability verification and no version info
        if was_network_error and not current_version:
            return "UNKNOWN"

        if not current_version or not latest_version:
            return "UNKNOWN"

        # Clean current version (strip operators like ==, >=, ^, ~)
        clean_cur = re.sub(r'^[=><~^!]+', '', current_version.strip())

        try:
            v_cur = pkg_version.parse(clean_cur)
            v_lat = pkg_version.parse(latest_version.strip())

            if v_cur < v_lat:
                return "OUTDATED"
            else:
                return "CURRENT"
        except Exception:
            # Fallback string comparison or mark UNKNOWN
            if clean_cur == latest_version.strip():
                return "CURRENT"
            return "UNKNOWN"
