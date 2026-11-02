from __future__ import annotations


class SaveFault:
    """保存工具的故障注入，在业务校验全部通过、即将写入时判定。

    once: 本次运行中首次进入写入阶段的保存失败；always: 每次都失败。
    """

    def __init__(self, mode: str | None = None):
        if mode not in (None, "once", "always"):
            raise ValueError(f"unsupported fault mode: {mode}")
        self.mode = mode
        self.triggered = 0

    def should_fail(self) -> bool:
        if self.mode == "always" or (self.mode == "once" and self.triggered == 0):
            self.triggered += 1
            return True
        return False


def parse_fault(value: str | None) -> str | None:
    """解析 CLI 参数 save=once|always。"""
    if not value:
        return None
    tool, _, mode = value.partition("=")
    if tool != "save" or mode not in ("once", "always"):
        raise ValueError("--fault 只支持 save=once 或 save=always")
    return mode
