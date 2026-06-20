"""Generate the required password-reset PDF using only the Python standard library."""
from pathlib import Path


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path: Path) -> None:
    lines = [
        "Password Reset and Account Recovery Guide",
        "Use Forgot password on the sign-in page and enter the verified account email.",
        "The reset link expires after 30 minutes and can be used only once.",
        "Check spam and allow emails from support@adsparkx.example if the message is missing.",
        "After five failed sign-in attempts, the account is locked for 15 minutes.",
        "Support cannot view passwords or bypass multi-factor authentication.",
        "If the verified email is unavailable, escalate for identity verification.",
    ]
    stream_lines = ["BT", "/F1 16 Tf", "72 740 Td"]
    for index, line in enumerate(lines):
        if index == 1:
            stream_lines.extend(["/F1 11 Tf", "0 -30 Td"])
        elif index > 1:
            stream_lines.append("0 -22 Td")
        stream_lines.append(f"({escape(line)}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n%ADSX\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)


if __name__ == "__main__":
    write_pdf(Path("data/password_reset_guide.pdf"))

