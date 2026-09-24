# Captura la ventana de Chrome mostrando la pestana cuyo titulo contiene $Match (evidencias del informe).
# Si la pestana no esta activa, recorre pestanas con Ctrl+PageDown hasta encontrarla.
# Uso: powershell -File snap.ps1 <archivo.png> [texto_del_titulo]
param([string]$Out, [string]$Match = "CacaoSense")
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr p);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int a, out RECT r, int s);
  public struct RECT { public int L, T, R, B; }
  public static string Title(IntPtr h) { var sb = new StringBuilder(512); GetWindowText(h, sb, 512); return sb.ToString(); }
  public static IntPtr Find(string m) { IntPtr found = IntPtr.Zero;
    EnumWindows((h, p) => { if (!IsWindowVisible(h)) return true; string t = Title(h);
      if (t.EndsWith("Google Chrome") && (m == "" || t.Contains(m))) { found = h; return false; } return true; }, IntPtr.Zero);
    return found; }
}
"@
[W]::SetProcessDPIAware() | Out-Null
$h = [W]::Find($Match)
if ($h -eq [IntPtr]::Zero) {
  $h = [W]::Find("")
  [W]::ShowWindow($h, 9) | Out-Null; [W]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 500
  for ($i = 0; $i -lt 25 -and -not ([W]::Title($h)).Contains($Match); $i++) {
    [System.Windows.Forms.SendKeys]::SendWait("^{PGDN}"); Start-Sleep -Milliseconds 350 }
  if (-not ([W]::Title($h)).Contains($Match)) { throw "No se encontro pestana '$Match'" }
}
[W]::ShowWindow($h, 3) | Out-Null
[W]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 1500
$r = New-Object W+RECT
[W]::DwmGetWindowAttribute($h, 9, [ref]$r, 16) | Out-Null
$w = $r.R - $r.L; $hh = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $hh
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
"$Out ${w}x${hh} [$([W]::Title($h))]"
