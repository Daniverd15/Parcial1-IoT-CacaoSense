# Pone al frente la pestana de Chrome cuyo titulo contiene $Want, recorriendo con Ctrl+Tab las ventanas de Chrome.
#   powershell -ExecutionPolicy Bypass -File tools\front_tab.ps1 "Explorador de datos"
param([string]$Want)
Add-Type @"
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text;
public class FT { public delegate bool P(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] static extern bool EnumWindows(P f, IntPtr p);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
 public static string Title(IntPtr h){ var sb=new StringBuilder(512); GetWindowText(h,sb,512); return sb.ToString(); }
 public static List<IntPtr> Chrome(){ var l=new List<IntPtr>(); EnumWindows((h,p)=>{ if(IsWindowVisible(h)&&Title(h).EndsWith("Google Chrome")) l.Add(h); return true;}, IntPtr.Zero); return l; } }
"@
Add-Type -AssemblyName System.Windows.Forms
$sh = New-Object -ComObject WScript.Shell
foreach ($h in [FT]::Chrome()) {
    [FT]::ShowWindow($h, 9) | Out-Null; $sh.SendKeys('%'); [FT]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 500
    $first = [FT]::Title($h)
    for ($i = 0; $i -lt 12; $i++) {
        if ([FT]::Title($h) -like "*$Want*") { "ok: " + [FT]::Title($h); exit 0 }
        [System.Windows.Forms.SendKeys]::SendWait("^{TAB}"); Start-Sleep -Milliseconds 400
        if ([FT]::Title($h) -eq $first) { break }
    }
}
"no encontrada: $Want"; exit 1
