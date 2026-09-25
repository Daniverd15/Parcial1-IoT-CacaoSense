# Activa una ventana de VS Code por titulo y ejecuta un comando de la paleta (F1).
#   powershell -ExecutionPolicy Bypass -File tools\vscode_cmd.ps1 "riego - Visual Studio Code" "Wokwi: Start Simulator" [salida.png]
param([string]$Title, [string]$Command, [string]$Shot = "")
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr p);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  public struct RECT { public int L, T, R, B; }
}
"@
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[W]::SetProcessDPIAware() | Out-Null
$script:hwnd = [IntPtr]::Zero
[W]::EnumWindows({ param($h, $p)
    $sb = New-Object Text.StringBuilder 512
    [W]::GetWindowText($h, $sb, 512) | Out-Null
    if ([W]::IsWindowVisible($h) -and $sb.ToString() -like "*$Title*") { $script:hwnd = $h; return $false }
    return $true }, [IntPtr]::Zero) | Out-Null
if ($script:hwnd -eq [IntPtr]::Zero) { "ventana no encontrada: $Title"; exit 1 }
[W]::ShowWindow($script:hwnd, 9) | Out-Null
$sh = New-Object -ComObject WScript.Shell
$sh.SendKeys('%')                      # Windows solo cede el foco tras una pulsacion de teclado
[W]::SetForegroundWindow($script:hwnd) | Out-Null
$sb2 = New-Object Text.StringBuilder 512
Start-Sleep -Milliseconds 300
Start-Sleep -Milliseconds 700
if ([W]::GetForegroundWindow() -ne $script:hwnd) { "no se pudo traer al frente: $Title"; exit 2 }
if ($Command) {
    [System.Windows.Forms.SendKeys]::SendWait("{F1}")
    Start-Sleep -Milliseconds 700
    [System.Windows.Forms.SendKeys]::SendWait($Command)
    Start-Sleep -Milliseconds 900
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Seconds 4
}
if ($Shot) {
    $r = New-Object W+RECT; [W]::GetWindowRect($script:hwnd, [ref]$r) | Out-Null
    $bmp = New-Object Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
    $g = [Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
    $bmp.Save($Shot, [Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
}
"ok"
