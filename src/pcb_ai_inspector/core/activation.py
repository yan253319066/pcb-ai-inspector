"""
PCB AI Inspector 授权系统模块。

提供离线许可证激活，包括：
- 硬件指纹生成
- 许可证密钥验证
- 激活状态管理
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import platform
import uuid as uuid_module


# 许可证状态
class LicenseState:
    """许可证状态枚举。"""

    UNLICENSED = "unlicensed"
    EVALUATION = "evaluation"
    ACTIVATED = "activated"
    EXPIRED = "expired"


@dataclass
class ActivationInfo:
    """当前激活状态的信息。"""

    state: str
    hardware_id: str
    activation_date: Optional[str] = None
    expiration_date: Optional[str] = None
    license_key: Optional[str] = None
    is_valid: bool = True
    message: str = ""


class HardwareFingerprint:
    """生成用于许可证绑定的唯一硬件指纹。"""

    @staticmethod
    def get_hardware_id() -> str:
        """根据机器特征生成唯一硬件 ID。

        结合多个标识符创建稳定、唯一的指纹：
        - 机器 ID (Windows)
        - UUID
        - 平台信息
        - 处理器信息

        Returns:
            唯一硬件 ID 字符串 (32 字符)
        """
        # 收集硬件标识符
        identifiers = []

        # 平台信息
        identifiers.append(platform.system())
        identifiers.append(platform.machine())
        identifiers.append(platform.processor() or "unknown")

        # 尝试获取 Windows 机器 GUID
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                identifiers.append(machine_guid)
        except Exception:
            # 回退到随机 UUID (将本地存储)
            machine_id = HardwareFingerprint._get_or_create_machine_id()
            identifiers.append(machine_id)

        # 网络 MAC 地址 (如果可用)
        try:
            mac = HardwareFingerprint._get_mac_address()
            if mac:
                identifiers.append(mac)
        except Exception:
            pass

        # 生成指纹哈希
        combined = "|".join(identifiers).encode("utf-8")
        fingerprint = hashlib.sha256(combined).hexdigest()[:32].upper()

        return fingerprint

    @staticmethod
    def _get_or_create_machine_id() -> str:
        """获取或创建持久化的机器 ID。

        Returns:
            机器 ID 字符串
        """
        config_dir = Path.home() / ".pcb-ai-inspector"
        config_dir.mkdir(parents=True, exist_ok=True)

        id_file = config_dir / ".machine_id"

        if id_file.exists():
            return id_file.read_text(encoding="utf-8").strip()

        # Generate new machine ID
        machine_id = str(uuid.uuid4()).upper()
        id_file.write_text(machine_id, encoding="utf-8")

        return machine_id

    @staticmethod
    def _get_mac_address() -> Optional[str]:
        """获取主 MAC 地址。

        Returns:
            MAC 地址字符串或 None
        """
        try:
            import uuid as uuid_module

            mac = uuid_module.getnode()
            # Format as standard MAC address
            return ":".join(f"{(mac >> i) & 0xFF:02x}" for i in range(0, 48, 8)[::-1])
        except Exception:
            return None


class LicenseKey:
    """许可证密钥生成和验证。"""

    # 密钥格式: XXXX-XXXX-XXXX-XXXX (16 个字母数字字符)
    KEY_FORMAT = "{:04}-{:04}-{:04}-{:04}"

    @staticmethod
    def generate_key(hardware_id: str) -> str:
        """为指定硬件 ID 生成许可证密钥。

        注意：生产环境中应在服务器端完成。
        此方法用于生成有效的测试密钥。

        Args:
            hardware_id: 硬件指纹

        Returns:
            许可证密钥字符串
        """
        # 基于硬件 ID 创建确定性密钥
        key_data = f"LICENSE-{hardware_id}-2024"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16].upper()

        # 格式化为 XXXX-XXXX-XXXX-XXXX
        chunks = [key_hash[i : i + 4] for i in range(0, 16, 4)]
        return "-".join(chunks)

    @staticmethod
    def validate_format(key: str) -> bool:
        """检查密钥格式是否正确。

        Args:
            key: 许可证密钥字符串

        Returns:
            格式有效返回 True
        """
        if not key:
            return False

        # Remove any whitespace
        key = key.strip().upper()

        # Check format: XXXX-XXXX-XXXX-XXXX
        parts = key.split("-")
        if len(parts) != 4:
            return False

        for part in parts:
            if len(part) != 4:
                return False
            if not part.isalnum():
                return False

        return True

    @staticmethod
    def validate_key(key: str, hardware_id: str) -> bool:
        """验证许可证密钥与硬件 ID 是否匹配。

        Args:
            key: 许可证密钥字符串
            hardware_id: 硬件指纹

        Returns:
            密钥对该硬件有效返回 True
        """
        if not LicenseKey.validate_format(key):
            return False

        # 对于此简单实现，我们接受：
        # 1. 符合我们生成格式的密钥
        # 2. 演示密钥用于评估

        key_clean = key.strip().upper().replace("-", "")

        # 演示密钥 (用于测试)
        if key_clean == "DEMO2024PCB":
            return True

        # 生成密钥验证
        expected_key = LicenseKey.generate_key(hardware_id).replace("-", "")
        if key_clean == expected_key:
            return True

        return False


class ActivationManager:
    """管理许可证激活状态。"""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """初始化激活管理器。

        Args:
            config_dir: 存储激活数据的目录
        """
        if config_dir is None:
            config_dir = Path.home() / ".pcb-ai-inspector"

        self._config_dir = config_dir
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._activation_file = self._config_dir / "activation.json"

        # 获取硬件 ID
        self._hardware_id = HardwareFingerprint.get_hardware_id()

        # 加载激活状态
        self._activation_data: dict = self._load_activation_data()

    def _load_activation_data(self) -> dict:
        """从文件加载激活数据。

        Returns:
            激活数据字典
        """
        if self._activation_file.exists():
            try:
                return json.loads(self._activation_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "state": LicenseState.UNLICENSED,
            "hardware_id": self._hardware_id,
        }

    def _save_activation_data(self) -> None:
        """保存激活数据到文件。"""
        self._activation_file.write_text(
            json.dumps(self._activation_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_activation_info(self) -> ActivationInfo:
        """获取当前激活信息。

        Returns:
            包含当前状态的 ActivationInfo
        """
        state = self._activation_data.get("state", LicenseState.UNLICENSED)

        # Check if hardware ID matches
        stored_hardware_id = self._activation_data.get("hardware_id", "")
        hardware_match = stored_hardware_id == self._hardware_id

        # Check expiration
        expiration_date_str = self._activation_data.get("expiration_date")
        expiration_date = None
        is_expired = False

        if expiration_date_str:
            try:
                expiration_date = datetime.fromisoformat(expiration_date_str)
                is_expired = datetime.now() > expiration_date
            except Exception:
                pass

        # Update state if expired
        if state == LicenseState.ACTIVATED and is_expired:
            state = LicenseState.EXPIRED
            self._activation_data["state"] = state
            self._save_activation_data()

        # Determine validity
        is_valid = state == LicenseState.ACTIVATED and hardware_match and not is_expired

        # Generate message
        if state == LicenseState.UNLICENSED:
            message = "软件未激活。请输入授权码进行激活。"
        elif state == LicenseState.EVALUATION:
            message = f"试用版。{'已过期' if is_expired else f'剩余 {self._get_days_remaining(expiration_date)} 天'}"
        elif state == LicenseState.ACTIVATED:
            message = "软件已激活。" if hardware_match else "硬件ID不匹配，请联系支持。"
        elif state == LicenseState.EXPIRED:
            message = "授权已过期。请续期或重新激活。"
        else:
            message = "未知授权状态。"

        return ActivationInfo(
            state=state,
            hardware_id=self._hardware_id,
            activation_date=self._activation_data.get("activation_date"),
            expiration_date=expiration_date_str,
            license_key=self._activation_data.get("license_key"),
            is_valid=is_valid,
            message=message,
        )

    @staticmethod
    def _get_days_remaining(expiration_date: Optional[datetime]) -> int:
        """获取距离过期的剩余天数。

        Args:
            expiration_date: 过期时间 datetime

        Returns:
            剩余天数 (过期或 None 时返回 0)
        """
        if expiration_date is None:
            return 0
        delta = expiration_date - datetime.now()
        return max(0, delta.days)

    def activate(self, license_key: str) -> tuple[bool, str]:
        """Activate the software with a license key.

        Args:
            license_key: License key string

        Returns:
            Tuple of (success, message)
        """
        # Validate key format
        if not LicenseKey.validate_format(license_key):
            return False, "授权码格式无效。正确的格式: XXXX-XXXX-XXXX-XXXX"

        # Validate key against hardware
        if not LicenseKey.validate_key(license_key, self._hardware_id):
            return False, "授权码无效或与当前硬件不匹配。"

        # Activate
        self._activation_data = {
            "state": LicenseState.ACTIVATED,
            "hardware_id": self._hardware_id,
            "license_key": license_key.strip().upper(),
            "activation_date": datetime.now().isoformat(),
            "activation_version": "1.0.0",
        }
        self._save_activation_data()

        return True, "激活成功！感谢您的支持。"

    def start_evaluation(self, days: int = 30) -> ActivationInfo:
        """Start an evaluation period.

        Args:
            days: Number of evaluation days

        Returns:
            Updated activation info
        """
        expiration_date = datetime.now() + timedelta(days=days)

        self._activation_data = {
            "state": LicenseState.EVALUATION,
            "hardware_id": self._hardware_id,
            "activation_date": datetime.now().isoformat(),
            "expiration_date": expiration_date.isoformat(),
        }
        self._save_activation_data()

        return self.get_activation_info()

    def deactivate(self) -> None:
        """Deactivate the current license."""
        self._activation_data = {
            "state": LicenseState.UNLICENSED,
            "hardware_id": self._hardware_id,
        }
        self._save_activation_data()

    def is_valid(self) -> bool:
        """Check if the current activation is valid.

        Returns:
            True if software is activated and valid
        """
        return self.get_activation_info().is_valid


# Convenience function
def check_activation() -> ActivationInfo:
    """Check current activation status.

    Returns:
        ActivationInfo with current state
    """
    manager = ActivationManager()
    return manager.get_activation_info()


if __name__ == "__main__":
    # 测试激活系统
    print("=" * 50)
    print("激活系统测试")
    print("=" * 50)

    # 硬件 ID
    hardware_id = HardwareFingerprint.get_hardware_id()
    print(f"硬件 ID: {hardware_id}")

    # 生成测试密钥
    test_key = LicenseKey.generate_key(hardware_id)
    print(f"生成的密钥: {test_key}")
    print(f"密钥格式正确: {LicenseKey.validate_format(test_key)}")

    # 激活管理器
    manager = ActivationManager()
    info = manager.get_activation_info()
    print(f"\n当前状态: {info.state}")
    print(f"消息: {info.message}")

    # 测试激活
    print("\n--- 测试激活 ---")
    success, message = manager.activate(test_key)
    print(f"激活结果: {success} - {message}")

    # 验证
    info = manager.get_activation_info()
    print(f"激活后: {info.state}, 有效: {info.is_valid}")
