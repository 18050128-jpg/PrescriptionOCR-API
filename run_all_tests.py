"""Chạy pytest, ghi kết quả ra file để đọc."""
import subprocess, sys, os

cwd = os.path.dirname(os.path.abspath(__file__))

groups = [
    ("test_json_store",   ["app/test/test_json_store.py"]),
    ("test_auth",         ["app/test/test_auth.py"]),
    ("test_prescription", ["app/test/test_prescription.py"]),
    ("test_reminder",     ["app/test/test_reminder.py"]),
    ("test_notification", ["app/test/test_notification.py"]),
    ("test_admin",        ["app/test/test_admin.py"]),
]

out_lines = []
summary = []

for name, paths in groups:
    result = subprocess.run(
        [sys.executable, "-m", "pytest"] + paths +
        ["-v", "--tb=short", "-p", "no:warnings"],
        capture_output=True, text=True, encoding="utf-8", cwd=cwd,
    )
    out_lines.append(f"\n{'='*60}\n{name}\n{'='*60}")
    out_lines.append(result.stdout)
    if result.returncode != 0:
        out_lines.append("STDERR: " + result.stderr[:500])
    # Lấy dòng tóm tắt cuối
    for line in reversed(result.stdout.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            summary.append(f"[{name}] {line.strip()}")
            break

out_lines.append("\n" + "="*60)
out_lines.append("SUMMARY")
out_lines.append("="*60)
out_lines.extend(summary)

output = "\n".join(out_lines)
out_path = os.path.join(cwd, "test_result.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(output)

print(output)
