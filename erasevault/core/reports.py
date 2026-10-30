"""
Detailed, tamper-evident sanitization certificate and report generator for EraseVault.
Exports structured reports in HTML, JSON, and Plain Text (.txt) formats with SHA-256 verification.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
from typing import Dict, Tuple

from .models import OperationRecord, format_bytes


class ReportGenerator:
    """Generates detailed sanitization reports and certificates with cryptographic integrity digests."""

    @staticmethod
    def compute_report_digest(record: OperationRecord) -> str:
        canonical = json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def export_json_report(cls, record: OperationRecord, output_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        payload = {
            "report_schema": "EraseVault-Audit-Report-v1.0",
            "operation": record.to_dict(),
            "report_sha256": cls.compute_report_digest(record),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return os.path.abspath(output_path)

    @classmethod
    def verify_json_report_integrity(cls, json_path: str) -> Tuple[bool, str]:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            op_dict = data.get("operation", {})
            expected_hash = data.get("report_sha256", "")
            rec = OperationRecord.from_dict(op_dict)
            actual_hash = cls.compute_report_digest(rec)
            if expected_hash and expected_hash == actual_hash:
                return (True, f"Integrity Verified (SHA-256: {actual_hash[:24]}...)")
            return (False, "Digest mismatch: Report content has been modified since generation.")
        except Exception as exc:
            return (False, f"Failed to verify report file: {exc}")

    @classmethod
    def generate_text_report(cls, record: OperationRecord) -> str:
        digest = cls.compute_report_digest(record)
        ver = record.verification
        lines = [
            "==============================================================================",
            "                ERASEVAULT DATA SANITIZATION AUDIT REPORT                     ",
            "==============================================================================",
            f"Operation ID       : {record.op_id}",
            f"Operation Type     : {record.operation_type}",
            f"Sanitization Method: {record.method_name} ({record.method_id})",
            f"Passes Completed   : {record.passes_completed}",
            f"Operation Status   : {record.status}",
            f"Start Timestamp    : {record.timestamp_start}",
            f"End Timestamp      : {record.timestamp_end}",
            f"Duration           : {record.duration_seconds:.2f} seconds",
            f"Storage Media Type : {record.media_summary}",
            f"Bytes Processed    : {format_bytes(record.total_bytes_processed)} ({record.total_bytes_processed:,} B)",
            f"Files Erased       : {record.files_erased}",
            f"Folders Removed    : {record.folders_removed}",
            f"Host System        : {record.host_info.get('os', 'Unknown')} ({record.host_info.get('hostname', '')})",
            "------------------------------------------------------------------------------",
            "TARGET MANIFEST:",
        ]
        for t in record.targets:
            lines.append(f"  - {t}")

        lines.append("------------------------------------------------------------------------------")
        lines.append("VERIFICATION & HARDWARE LIMITATIONS:")
        if ver:
            lines.extend(
                [
                    f"  Verification Status : {ver.verification_level.value}",
                    f"  Path Removal Check  : {'PASSED (Removed)' if ver.path_removed else 'FAILED'}",
                    f"  Bytes Sampled       : {format_bytes(ver.bytes_sampled)} ({ver.bytes_sampled:,} B)",
                    f"  Zero-Byte Ratio     : {ver.zero_ratio * 100:.2f}%",
                    f"  Sample Entropy      : {ver.entropy_bits_per_byte:.4f} bits/byte",
                    f"  Residual Signatures : {', '.join(ver.residual_signatures_found) if ver.residual_signatures_found else 'None Detected (0)'}",
                    f"  Summary             : {ver.summary}",
                    f"  Hardware Disclosure : {ver.hardware_caveat}",
                    f"  Verification Digest : {ver.certificate_sha256}",
                ]
            )
        else:
            lines.append("  Verification was not executed for this operation.")

        if record.warnings:
            lines.append("------------------------------------------------------------------------------")
            lines.append("WARNINGS & HARDWARE NOTICES:")
            for w in record.warnings:
                lines.append(f"  [!] {w}")

        if record.errors:
            lines.append("------------------------------------------------------------------------------")
            lines.append("ERRORS:")
            for e in record.errors:
                lines.append(f"  [ERROR] {e}")

        lines.extend(
            [
                "------------------------------------------------------------------------------",
                f"Report SHA-256 Digest : {digest}",
                "==============================================================================",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def export_text_report(cls, record: OperationRecord, output_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        text = cls.generate_text_report(record)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        return os.path.abspath(output_path)

    @classmethod
    def generate_html_report(cls, record: OperationRecord) -> str:
        digest = cls.compute_report_digest(record)
        ver = record.verification
        e = html.escape

        targets_html = "".join(f"<li><code>{e(t)}</code></li>" for t in record.targets)
        warnings_html = (
            "".join(f"<div class='warn-item'>{e(w)}</div>" for w in record.warnings)
            if record.warnings
            else "<div class='muted'>None</div>"
        )
        errors_html = (
            "".join(f"<div class='err-item'>{e(err)}</div>" for err in record.errors)
            if record.errors
            else "<div class='muted'>None (0 errors)</div>"
        )

        ver_html = "<p class='muted'>Verification was not requested for this operation.</p>"
        if ver:
            ver_html = f"""
            <table class="meta-table">
              <tr><th>Verification Level</th><td><strong>{e(ver.verification_level.value)}</strong></td></tr>
              <tr><th>Target Path Unlinked</th><td>{'Yes (Verified Removed)' if ver.path_removed else 'No'}</td></tr>
              <tr><th>Sampled Verification Bytes</th><td>{e(format_bytes(ver.bytes_sampled))} ({ver.bytes_sampled:,} B)</td></tr>
              <tr><th>Sample Zero Ratio / Entropy</th><td>{ver.zero_ratio*100:.2f}% zeros | {ver.entropy_bits_per_byte:.4f} bits/byte</td></tr>
              <tr><th>Residual File Signatures</th><td>{e(', '.join(ver.residual_signatures_found) if ver.residual_signatures_found else 'None Detected (0)')}</td></tr>
              <tr><th>Assessment Summary</th><td>{e(ver.summary)}</td></tr>
              <tr><th>Hardware &amp; SSD Disclosure</th><td class="caveat">{e(ver.hardware_caveat)}</td></tr>
              <tr><th>Verification Certificate Hash</th><td><code>{e(ver.certificate_sha256)}</code></td></tr>
            </table>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>EraseVault Sanitization Report — {e(record.op_id)}</title>
<style>
  body {{ font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; background: #F3F7FD; color: #0F172A; margin: 28px; }}
  .card {{ background: #FFFFFF; border: 1px solid #DCE7F7; border-radius: 14px; padding: 28px 32px; max-width: 920px; margin: 0 auto; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #E8F0FC; padding-bottom: 16px; margin-bottom: 20px; }}
  .brand {{ font-size: 24px; font-weight: 800; color: #061937; }}
  .brand span {{ color: #096DFD; }}
  .badge {{ background: #ECF4FE; color: #096DFD; border: 1px solid #3B83FF; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }}
  h2 {{ font-size: 16px; color: #1E3A5F; margin-top: 24px; margin-bottom: 10px; border-left: 4px solid #096DFD; padding-left: 10px; }}
  .meta-table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
  .meta-table th, .meta-table td {{ text-align: left; padding: 9px 12px; border-bottom: 1px solid #EDF3FC; vertical-align: top; }}
  .meta-table th {{ width: 240px; color: #475569; font-weight: 600; background: #FAFCFE; }}
  code {{ background: #F1F5F9; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 12.5px; }}
  .warn-item {{ background: #FEF9C3; border: 1px solid #FDE047; color: #854D0E; padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; }}
  .err-item {{ background: #FEE2E2; border: 1px solid #FCA5A5; color: #991B1B; padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; }}
  .caveat {{ color: #334155; line-height: 1.45; }}
  .footer {{ margin-top: 24px; padding-top: 14px; border-top: 1px solid #E2E8F0; font-size: 12px; color: #64748B; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div>
      <div class="brand">Erase<span>Vault</span></div>
      <div style="color:#475569;font-size:13px;">Secure Data Sanitization Audit Certificate</div>
    </div>
    <div class="badge">{e(record.status)}</div>
  </div>

  <h2>Operation Summary</h2>
  <table class="meta-table">
    <tr><th>Operation ID</th><td><code>{e(record.op_id)}</code></td></tr>
    <tr><th>Operation Type</th><td>{e(record.operation_type)}</td></tr>
    <tr><th>Sanitization Method</th><td><strong>{e(record.method_name)}</strong> ({record.passes_completed} pass(es))</td></tr>
    <tr><th>Start / End (UTC)</th><td>{e(record.timestamp_start)} &rarr; {e(record.timestamp_end)} ({record.duration_seconds:.2f}s)</td></tr>
    <tr><th>Detected Storage Media</th><td>{e(record.media_summary)}</td></tr>
    <tr><th>Bytes Overwritten</th><td>{e(format_bytes(record.total_bytes_processed))} ({record.total_bytes_processed:,} bytes)</td></tr>
    <tr><th>Files &amp; Folders Sanitized</th><td>{record.files_erased} file(s), {record.folders_removed} folder(s)</td></tr>
    <tr><th>Host Environment</th><td>{e(record.host_info.get('os', 'Unknown'))} — {e(record.host_info.get('hostname', ''))}</td></tr>
  </table>

  <h2>Sanitized Target Manifest</h2>
  <ul>{targets_html}</ul>

  <h2>Post-Erasure Verification &amp; Hardware Assessment</h2>
  {ver_html}

  <h2>Hardware Notices &amp; Warnings</h2>
  {warnings_html}

  <h2>Error Log</h2>
  {errors_html}

  <div class="footer">
    Tamper-Evident Report SHA-256 Digest: <code>{digest}</code>
  </div>
</div>
</body>
</html>"""

    @classmethod
    def export_html_report(cls, record: OperationRecord, output_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        html_str = cls.generate_html_report(record)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_str)
        return os.path.abspath(output_path)
